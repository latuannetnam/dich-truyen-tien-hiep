"""Translation engine with chunking and context management."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from dich_truyen.config import TranslationConfig, get_config
from dich_truyen.translator.glossary import Glossary, generate_glossary_from_samples
from dich_truyen.translator.llm import LLMClient
from dich_truyen.translator.style import StyleManager, StyleTemplate
from dich_truyen.utils.progress import BookProgress, ChapterStatus

console = Console()


class TranslationResult(BaseModel):
    """Result of translation operation."""

    total_chapters: int
    translated: int
    skipped: int
    failed: int
    errors: list[str] = []


class TranslationEngine:
    """Main translation engine with chunking and context management."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        style: Optional[StyleTemplate] = None,
        glossary: Optional[Glossary] = None,
        config: Optional[TranslationConfig] = None,
    ):
        """Initialize the translation engine.

        Args:
            llm: LLM client instance
            style: Style template for translation
            glossary: Glossary for consistent terms
            config: Translation configuration
        """
        self.llm = llm or LLMClient()
        self.style = style
        self.glossary = glossary or Glossary()
        self.config = config or get_config().translation

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks by character count, respecting paragraphs.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        chunk_size = self.config.chunk_size
        paragraphs = text.split("\n\n")

        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para)

            # If single paragraph exceeds chunk size, split it
            if para_length > chunk_size:
                # Flush current chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split long paragraph by sentences
                sentences = re.split(r"([。！？])", para)
                sentence_buffer = ""

                for i, part in enumerate(sentences):
                    sentence_buffer += part
                    if part in "。！？" or i == len(sentences) - 1:
                        if len(sentence_buffer) > chunk_size:
                            # Force split mid-sentence
                            while sentence_buffer:
                                chunks.append(sentence_buffer[:chunk_size])
                                sentence_buffer = sentence_buffer[chunk_size:]
                        elif current_length + len(sentence_buffer) > chunk_size:
                            chunks.append("\n\n".join(current_chunk))
                            current_chunk = [sentence_buffer]
                            current_length = len(sentence_buffer)
                        else:
                            current_chunk.append(sentence_buffer)
                            current_length += len(sentence_buffer)
                        sentence_buffer = ""

            elif current_length + para_length + 2 > chunk_size:
                # Flush current chunk and start new one
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length + 2  # +2 for \n\n

        # Don't forget the last chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    async def translate_chunk(
        self,
        chunk: str,
        context: Optional[str] = None,
    ) -> str:
        """Translate a single chunk of text.

        Args:
            chunk: Text chunk to translate
            context: Previous context for continuity

        Returns:
            Translated text
        """
        if not self.style:
            raise ValueError("Style template not set")

        style_prompt = self.style.to_prompt_format()
        glossary_prompt = self.glossary.to_prompt_format() if self.glossary else ""

        return await self.llm.translate(
            text=chunk,
            style_prompt=style_prompt,
            glossary_prompt=glossary_prompt,
            context=context,
        )

    async def translate_chapter(
        self,
        chapter_path: Path,
        output_path: Path,
    ) -> str:
        """Translate an entire chapter file.

        Args:
            chapter_path: Path to source chapter file
            output_path: Path to save translated chapter

        Returns:
            Translated chapter content
        """
        # Read source chapter
        with open(chapter_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into chunks
        chunks = self.chunk_text(content)

        # Translate each chunk with context
        translated_chunks = []
        context = None

        for chunk in chunks:
            translated = await self.translate_chunk(chunk, context)
            translated_chunks.append(translated)

            # Use last ~500 chars as context for next chunk
            context = translated[-500:] if len(translated) > 500 else translated

        # Combine translated chunks
        result = "\n\n".join(translated_chunks)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save translated chapter
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

        return result

    async def translate_book(
        self,
        book_dir: Path,
        resume: bool = True,
    ) -> TranslationResult:
        """Translate all chapters in a book.

        Args:
            book_dir: Book directory path
            resume: Whether to skip already translated chapters

        Returns:
            Translation result with statistics
        """
        book_dir = Path(book_dir)
        raw_dir = book_dir / "raw"
        translated_dir = book_dir / "translated"

        # Ensure directories exist
        translated_dir.mkdir(exist_ok=True)

        # Load book progress
        progress = BookProgress.load(book_dir)
        if not progress:
            raise ValueError(f"Book not initialized: {book_dir}")

        # Get chapters to translate
        if resume:
            chapters_to_translate = progress.get_pending_chapters("translate")
        else:
            chapters_to_translate = [
                c for c in progress.chapters if c.status in (ChapterStatus.CRAWLED, ChapterStatus.TRANSLATED)
            ]

        if not chapters_to_translate:
            console.print("[green]All chapters already translated![/green]")
            return TranslationResult(
                total_chapters=len(progress.chapters),
                translated=0,
                skipped=len(progress.chapters),
                failed=0,
            )

        console.print(f"[blue]Translating {len(chapters_to_translate)} chapters...[/blue]")

        result = TranslationResult(
            total_chapters=len(progress.chapters),
            translated=0,
            skipped=len(progress.chapters) - len(chapters_to_translate),
            failed=0,
        )

        # Translate with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as pbar:
            task = pbar.add_task("Translating", total=len(chapters_to_translate))

            for chapter in chapters_to_translate:
                pbar.update(
                    task, description=f"Ch.{chapter.index}: {chapter.title_cn[:20]}..."
                )

                try:
                    # Find source file
                    source_files = list(raw_dir.glob(f"{chapter.index:04d}_*.txt"))
                    if not source_files:
                        raise FileNotFoundError(f"Source file not found for chapter {chapter.index}")

                    source_path = source_files[0]
                    output_path = translated_dir / source_path.name

                    # Translate
                    await self.translate_chapter(source_path, output_path)

                    # Update status
                    progress.update_chapter_status(chapter.index, ChapterStatus.TRANSLATED)
                    result.translated += 1

                except Exception as e:
                    error_msg = f"Chapter {chapter.index}: {str(e)}"
                    result.errors.append(error_msg)
                    result.failed += 1
                    progress.update_chapter_status(
                        chapter.index, ChapterStatus.ERROR, str(e)
                    )
                    console.print(f"[red]Error: {error_msg}[/red]")

                # Save progress periodically
                if result.translated % 5 == 0:
                    progress.save(book_dir)

                pbar.advance(task)

        # Final save
        progress.save(book_dir)

        console.print(f"\n[green]Translation complete![/green]")
        console.print(f"  Translated: {result.translated}")
        console.print(f"  Skipped: {result.skipped}")
        console.print(f"  Failed: {result.failed}")

        return result


async def setup_translation(
    book_dir: Path,
    style_name: str = "tien_hiep",
    glossary_path: Optional[Path] = None,
    auto_glossary: bool = True,
) -> TranslationEngine:
    """Set up translation engine for a book.

    Args:
        book_dir: Book directory path
        style_name: Style template name
        glossary_path: Optional path to import glossary
        auto_glossary: Whether to auto-generate glossary

    Returns:
        Configured TranslationEngine
    """
    book_dir = Path(book_dir)

    # Load style
    style_manager = StyleManager()
    try:
        style = style_manager.load(style_name)
        console.print(f"[green]Loaded style: {style_name}[/green]")
    except ValueError:
        console.print(f"[yellow]Style not found: {style_name}, using default[/yellow]")
        style = style_manager.load("tien_hiep")

    # Load or create glossary
    if glossary_path:
        glossary = Glossary.from_csv(glossary_path)
    else:
        glossary = Glossary.load_or_create(book_dir)

    # Auto-generate glossary if empty and enabled
    if auto_glossary and len(glossary) == 0:
        console.print("[blue]Generating glossary from sample chapters...[/blue]")

        # Read first few chapters as samples
        raw_dir = book_dir / "raw"
        samples = []
        for txt_file in sorted(raw_dir.glob("*.txt"))[:3]:
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Take first 2000 chars from each
                samples.append(content[:2000])

        if samples:
            glossary = await generate_glossary_from_samples(samples, glossary)
            glossary.save(book_dir)
            console.print(f"[green]Generated {len(glossary)} glossary entries[/green]")

    return TranslationEngine(
        style=style,
        glossary=glossary,
    )
