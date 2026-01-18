"""Translation engine with chunking and context management."""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dich_truyen.translator.term_scorer import SimpleTermScorer

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
        term_scorer: Optional["SimpleTermScorer"] = None,
    ):
        """Initialize the translation engine.

        Args:
            llm: LLM client instance
            style: Style template for translation
            glossary: Glossary for consistent terms
            config: Translation configuration
            term_scorer: Optional TF-IDF scorer for intelligent glossary selection
        """
        self.llm = llm or LLMClient(task="translate")
        self.style = style
        self.glossary = glossary or Glossary()
        self.config = config or get_config().translation
        self.term_scorer = term_scorer

    def _is_dialogue_paragraph(self, para: str) -> bool:
        """Check if paragraph contains dialogue that should stay together.
        
        Chinese dialogue typically uses "" or 「」 quotes.
        """
        # Check for dialogue markers
        has_cn_quotes = '"' in para or '"' in para or '「' in para or '」' in para
        # Also check for dialogue attribution patterns
        has_attribution = any(marker in para for marker in ['说道', '道：', '说：', '问道', '笑道', '叫道'])
        return has_cn_quotes or has_attribution

    def _find_dialogue_block_end(self, paragraphs: list[str], start_idx: int) -> int:
        """Find the end of a dialogue block (consecutive dialogue paragraphs).
        
        Returns the index of the last paragraph in the dialogue block.
        """
        end_idx = start_idx
        for i in range(start_idx, len(paragraphs)):
            if self._is_dialogue_paragraph(paragraphs[i]):
                end_idx = i
            else:
                # Non-dialogue paragraph - check if it's short (could be narration between dialogue)
                if len(paragraphs[i]) < 100 and i + 1 < len(paragraphs) and self._is_dialogue_paragraph(paragraphs[i + 1]):
                    # Short narration between dialogue, include it
                    continue
                else:
                    break
        return end_idx

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks by character count, respecting paragraphs and dialogue blocks.

        This method ensures:
        1. Paragraphs are not split mid-way
        2. Dialogue blocks (conversations) are kept together when possible
        3. Chunks don't exceed chunk_size except for very long dialogue blocks

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
        i = 0

        while i < len(paragraphs):
            para = paragraphs[i]
            para_length = len(para)

            # Check if this starts a dialogue block
            if self._is_dialogue_paragraph(para):
                dialogue_end = self._find_dialogue_block_end(paragraphs, i)
                dialogue_block = paragraphs[i:dialogue_end + 1]
                dialogue_text = "\n\n".join(dialogue_block)
                dialogue_length = len(dialogue_text)

                # If dialogue block fits in current chunk, add it
                if current_length + dialogue_length + 2 <= chunk_size:
                    current_chunk.extend(dialogue_block)
                    current_length += dialogue_length + 2
                    i = dialogue_end + 1
                    continue
                
                # If dialogue block fits in a new chunk, flush current and start new
                if dialogue_length <= chunk_size * 1.2:  # Allow 20% overflow to keep dialogue together
                    if current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                    current_chunk = dialogue_block
                    current_length = dialogue_length
                    i = dialogue_end + 1
                    continue
                
                # Dialogue block too large - must split it (fall through to normal processing)

            # Normal paragraph processing
            if para_length > chunk_size:
                # Flush current chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split long paragraph by sentences
                sentences = re.split(r"([。！？])", para)
                sentence_buffer = ""

                for j, part in enumerate(sentences):
                    sentence_buffer += part
                    if part in "。！？" or j == len(sentences) - 1:
                        if len(sentence_buffer) > chunk_size:
                            while sentence_buffer:
                                chunks.append(sentence_buffer[:chunk_size])
                                sentence_buffer = sentence_buffer[chunk_size:]
                        elif current_length + len(sentence_buffer) > chunk_size:
                            if current_chunk:
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
                current_length += para_length + 2

            i += 1

        # Don't forget the last chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def annotate_with_glossary(self, text: str, max_terms: int = 30) -> str:
        """Annotate source text with glossary translations inline.
        
        Inserts glossary terms in format: 叶凡<Diệp Phàm>
        This enforces exact term usage by the LLM.
        
        Args:
            text: Source Chinese text to annotate
            max_terms: Maximum number of terms to annotate (most relevant)
            
        Returns:
            Annotated text with <Term> tags
        """
        if not self.glossary or len(self.glossary) == 0:
            return text
        
        # Get relevant terms for this text using TF-IDF scorer if available
        relevant_entries = self.glossary.get_relevant_entries(
            text, 
            scorer=self.term_scorer,
            max_entries=max_terms
        )
        
        if not relevant_entries:
            return text
        
        # Sort by length descending to prioritize longer terms (避免部分匹配)
        relevant_entries.sort(key=lambda e: -len(e.chinese))
        
        # Apply annotations with word boundaries
        for entry in relevant_entries:
            # Use whole-word boundary to avoid partial matches
            # (?<![...]) negative lookbehind: not preceded by letter/hanzi
            # (?![...]) negative lookahead: not followed by letter/hanzi
            pattern = re.compile(
                rf'(?<![a-zA-Z\u4e00-\u9fff])({re.escape(entry.chinese)})(?![a-zA-Z\u4e00-\u9fff])'
            )
            # Replace up to 5 occurrences per term to avoid bloat
            text = pattern.sub(rf'\1<{entry.vietnamese}>', text, count=5)
        
        return text

    def extract_state(self, response: str) -> tuple[str, dict]:
        """Extract translation and narrative state from LLM response.
        
        Parses the ---STATE--- marker and JSON block from the response.
        Falls back to empty state on parse errors.
        
        Args:
            response: LLM response text with optional state block
            
        Returns:
            Tuple of (translation_text, state_dict)
        """
        if "---STATE---" not in response:
            return response.strip(), {}
        
        try:
            parts = response.split("---STATE---", 1)
            translation = parts[0].strip()
            state_json = parts[1].strip()
            
            # Parse JSON robustly
            import json
            state = json.loads(state_json)
            
            # Validate state structure (optional fields)
            if not isinstance(state, dict):
                return translation, {}
            
            return translation, state
            
        except (json.JSONDecodeError, IndexError, Exception):
            # Fallback: return full response with empty state
            return response.strip(), {}

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
        # Use TF-IDF based relevant glossary selection if scorer available
        max_glossary = self.config.glossary_max_entries
        if self.glossary:
            glossary_prompt = self.glossary.format_relevant_entries(
                chunk, scorer=self.term_scorer, max_entries=max_glossary
            )
        else:
            glossary_prompt = ""

        return await self.llm.translate(
            text=chunk,
            style_prompt=style_prompt,
            glossary_prompt=glossary_prompt,
            context=context,
        )

    async def translate_chunk_with_context_marker(
        self,
        main_text: str,
        context_text: Optional[str] = None,
        narrative_state: Optional[dict] = None,
    ) -> str:
        """Translate text with a context portion that should not be included in output.

        Args:
            main_text: The main text to translate (this will be in the output)
            context_text: Context from previous portion (not included in output)
            narrative_state: Optional narrative state (speaker, pronouns) from previous chunk

        Returns:
            Translated main text only
        """
        if not self.style:
            raise ValueError("Style template not set")

        style_prompt = self.style.to_prompt_format()
        # Use TF-IDF based relevant glossary selection if scorer available
        max_glossary = self.config.glossary_max_entries
        if self.glossary:
            glossary_prompt = self.glossary.format_relevant_entries(
                main_text, scorer=self.term_scorer, max_entries=max_glossary
            )
        else:
            glossary_prompt = ""

        if context_text:
            # Use context as reference but only translate main_text
            return await self.llm.translate(
                text=main_text,
                style_prompt=style_prompt,
                glossary_prompt=glossary_prompt,
                context=context_text,  # Vietnamese context for reference
                narrative_state=narrative_state,
            )
        else:
            return await self.llm.translate(
                text=main_text,
                style_prompt=style_prompt,
                glossary_prompt=glossary_prompt,
                narrative_state=narrative_state,
            )

    async def _polish_translation(
        self,
        source_chinese: str,
        draft_vietnamese: str,
        progress_callback=None,
    ) -> str:
        """Polish a draft translation using Editor-in-Chief approach.

        Args:
            source_chinese: Original Chinese text
            draft_vietnamese: Draft Vietnamese translation
            progress_callback: Optional callback for progress updates

        Returns:
            Polished Vietnamese text, or draft if polish fails
        """
        if not self.style:
            raise ValueError("Style template not set")

        style_prompt = self.style.to_prompt_format()

        # Get relevant glossary for verification
        max_glossary = self.config.glossary_max_entries
        if self.glossary:
            glossary_prompt = self.glossary.format_relevant_entries(
                source_chinese, scorer=self.term_scorer, max_entries=max_glossary
            )
        else:
            glossary_prompt = ""

        max_retries = self.config.polish_max_retries
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                if progress_callback:
                    progress_callback(f"polishing (attempt {attempt + 1})")

                polished = await self.llm.polish(
                    source_chinese=source_chinese,
                    draft_vietnamese=draft_vietnamese,
                    style_prompt=style_prompt,
                    glossary_prompt=glossary_prompt,
                    temperature=self.config.polish_temperature,
                )
                return polished

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    console.print(f"[yellow]Polish attempt {attempt + 1} failed: {e}[/yellow]")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # All retries failed - fallback to draft
        console.print(f"[yellow]Polish failed after {max_retries + 1} attempts, using draft: {last_error}[/yellow]")
        return draft_vietnamese

    def create_chunks_with_context(self, text: str) -> list[dict]:
        """Split text into chunks with context from previous chunk.

        Each chunk includes context from the previous portion for translation quality,
        but only the main portion should be in the final output.

        Returns:
            List of dicts with 'main_text' and 'context_text' keys
        """
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        # First split by paragraphs using existing method
        raw_chunks = self.chunk_text(text)
        
        if len(raw_chunks) <= 1:
            # Single chunk, no context needed
            return [{"main_text": raw_chunks[0] if raw_chunks else "", "context_text": None}]
        
        result = []
        for i, chunk in enumerate(raw_chunks):
            if i == 0:
                # First chunk has no context
                result.append({"main_text": chunk, "context_text": None})
            else:
                # Use end of previous chunk as context (original Chinese)
                prev_chunk = raw_chunks[i - 1]
                context = prev_chunk[-overlap:] if len(prev_chunk) > overlap else prev_chunk
                result.append({"main_text": chunk, "context_text": context})
        
        return result

    async def translate_chapter(
        self,
        chapter_path: Path,
        output_path: Path,
        progress_callback=None,
    ) -> str:
        """Translate an entire chapter file using sequential chunk processing.
        
        Each chunk uses the TRANSLATED Vietnamese output from the previous chunk
        as context, improving pronoun resolution and term consistency.

        Args:
            chapter_path: Path to source chapter file
            output_path: Path to save translated chapter
            progress_callback: Optional callback for progress updates (chunk_idx, total_chunks, status)

        Returns:
            Translated chapter content
        """
        # Read source chapter
        with open(chapter_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into chunks
        chunks = self.chunk_text(content)
        total_chunks = len(chunks)
        
        if total_chunks == 0:
            return ""

        translated_chunks = []
        overlap = self.config.chunk_overlap
        
        # State tracking variables
        current_state = {}  # Narrative state from previous chunk
        state_extraction_failures = 0  # Counter for failed state extractions
        state_tracking_enabled = self.config.enable_state_tracking  # Can be disabled mid-chapter

        # Process chunks sequentially to use translated output as context
        for idx, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(idx, total_chunks, f"translating [{idx + 1}]")

            # SOLUTION 1: Annotate with glossary terms if enabled
            if self.config.enable_glossary_annotation:
                chunk = self.annotate_with_glossary(chunk, max_terms=30)
            
            # Build context from previous chunk
            if idx == 0:
                context_text = None
            else:
                prev_translated = translated_chunks[-1]
                # Take last 'overlap' characters as context
                context_text = prev_translated[-overlap:] if len(prev_translated) > overlap else prev_translated

            # SOLUTION 2: Inject state into translation call if enabled and available
            response = await self.translate_chunk_with_context_marker(
                main_text=chunk,
                context_text=context_text,
                narrative_state=current_state if state_tracking_enabled else None,
            )
            
            # Extract translation and state
            if state_tracking_enabled:
                translated, new_state = self.extract_state(response)
                
                # Check if state extraction succeeded
                if new_state:
                    current_state = new_state
                    state_extraction_failures = 0  # Reset counter on success
                else:
                    state_extraction_failures += 1
                    # Disable state tracking for this chapter after max retries
                    if state_extraction_failures >= self.config.state_tracking_max_retries:
                        state_tracking_enabled = False
                        current_state = {}
            else:
                translated = response
            
            # Reset state on scene breaks (detected by horizontal rules)
            if state_tracking_enabled and "---" in chunk and idx > 0:
                current_state = {}
            
            translated_chunks.append(translated)

        if progress_callback:
            progress_callback(total_chunks, total_chunks, "combining...")

        # Combine translated chunks
        draft_result = "\n\n".join(translated_chunks)

        # Polish pass (Editor-in-Chief)
        if self.config.enable_polish_pass:
            if progress_callback:
                progress_callback(total_chunks, total_chunks, "polishing...")

            result = await self._polish_translation(
                source_chinese=content,
                draft_vietnamese=draft_result,
                progress_callback=lambda status: progress_callback(total_chunks, total_chunks, status) if progress_callback else None,
            )
        else:
            result = draft_result

        if progress_callback:
            progress_callback(total_chunks, total_chunks, "[done]")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save translated chapter
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

        return result

    async def translate_book(
        self,
        book_dir: Path,
        chapters_spec: Optional[str] = None,
        resume: bool = True,
    ) -> TranslationResult:
        """Translate all chapters in a book.

        Args:
            book_dir: Book directory path
            chapters_spec: Optional chapter range (e.g., "1-100" or "1,5,10-20")
            resume: Whether to skip already translated chapters

        Returns:
            Translation result with statistics
        """
        from dich_truyen.utils.progress import parse_chapter_range
        
        book_dir = Path(book_dir)
        raw_dir = book_dir / "raw"
        translated_dir = book_dir / "translated"

        # Ensure directories exist
        translated_dir.mkdir(exist_ok=True)

        # Load book progress
        progress = BookProgress.load(book_dir)
        if not progress:
            raise ValueError(f"Book not initialized: {book_dir}")

        # Apply chapter range filter if specified
        all_chapters = progress.chapters
        max_chapter = len(all_chapters)
        
        if chapters_spec:
            indices = parse_chapter_range(chapters_spec, max_chapter)
            filtered_chapters = [c for c in all_chapters if c.index in indices]
        else:
            filtered_chapters = all_chapters

        # Get chapters to translate based on status
        if resume:
            chapters_to_translate = [
                c for c in filtered_chapters 
                if c.status == ChapterStatus.CRAWLED
            ]
        else:
            chapters_to_translate = [
                c for c in filtered_chapters 
                if c.status in (ChapterStatus.CRAWLED, ChapterStatus.TRANSLATED)
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

        # Pre-calculate total chunks for accurate progress tracking
        console.print("[dim]Calculating total chunks...[/dim]")
        total_chunks = 0
        for chapter in chapters_to_translate:
            source_files = list(raw_dir.glob(f"{chapter.index:04d}_*.txt"))
            if source_files:
                with open(source_files[0], "r", encoding="utf-8") as f:
                    content = f.read()
                chunks = self.chunk_text(content)
                total_chunks += len(chunks)

        # Translate with progress bar (tracking chunks not chapters)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as pbar:
            task = pbar.add_task("Translating", total=total_chunks)

            for chapter in chapters_to_translate:
                chapter_desc = f"Ch.{chapter.index}: {chapter.title_cn[:20]}..."
                pbar.update(task, description=chapter_desc)

                try:
                    # Find source file
                    source_files = list(raw_dir.glob(f"{chapter.index:04d}_*.txt"))
                    if not source_files:
                        raise FileNotFoundError(f"Source file not found for chapter {chapter.index}")

                    source_path = source_files[0]
                    # Use simple naming: chapter_number.txt
                    output_path = translated_dir / f"{chapter.index}.txt"

                    # Progress callback for chunk-level updates
                    def update_chunk_progress(chunk_idx, total_chunks_in_chapter, status=""):
                        desc = f"Ch.{chapter.index}: {chapter.title_cn[:12]}... {status} [{chunk_idx}/{total_chunks_in_chapter}]"
                        pbar.update(task, description=desc)
                        # Advance progress bar by 1 for each completed chunk
                        if "done" in status or status.startswith("[") and "translating" not in status:
                            pbar.advance(task, 1)

                    # Translate chapter content with chunk progress
                    await self.translate_chapter(source_path, output_path, update_chunk_progress)

                    # Translate chapter title if not already done
                    if chapter.title_cn and not chapter.title_vi:
                        chapter.title_vi = await self.llm.translate_title(
                            chapter.title_cn, "chapter"
                        )

                    # Progressive glossary: extract new terms from this chapter
                    if self.config.progressive_glossary and self.glossary:
                        from dich_truyen.translator.glossary import extract_new_terms_from_chapter
                        with open(source_path, "r", encoding="utf-8") as f:
                            chapter_content = f.read()
                        new_terms = await extract_new_terms_from_chapter(
                            chapter_content, self.glossary, max_new_terms=3
                        )
                        if new_terms:
                            for term in new_terms:
                                self.glossary.add(term)
                            console.print(f"[dim]  +{len(new_terms)} new glossary terms[/dim]")

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

                # Save progress after each chapter to prevent data loss
                progress.save(book_dir)
                
                # Save updated glossary if progressive mode enabled
                if self.config.progressive_glossary and self.glossary:
                    self.glossary.save(book_dir)

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
    from dich_truyen.config import log_llm_config_summary
    
    # Show LLM configuration
    log_llm_config_summary()
    
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

        # Get config values
        config = get_config().translation
        sample_chapter_count = config.glossary_sample_chapters
        sample_size = config.glossary_sample_size
        random_sample = config.glossary_random_sample
        min_entries = config.glossary_min_entries
        max_entries = config.glossary_max_entries

        # Read chapters for sampling
        raw_dir = book_dir / "raw"
        all_files = sorted(raw_dir.glob("*.txt"))
        
        # Select sample chapters
        if random_sample and len(all_files) > sample_chapter_count:
            import random
            sample_files = random.sample(all_files, sample_chapter_count)
            console.print(f"[dim]  Randomly selected {sample_chapter_count} chapters from {len(all_files)} available[/dim]")
        else:
            sample_files = all_files[:sample_chapter_count]
            console.print(f"[dim]  Using first {len(sample_files)} chapters[/dim]")
        
        samples = []
        for txt_file in sample_files:
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Take configured chars from each
                samples.append(content[:sample_size])

        if samples:
            glossary = await generate_glossary_from_samples(
                samples,
                style=style,
                existing_glossary=glossary,
                min_entries=min_entries,
                max_entries=max_entries,
            )
            glossary.save(book_dir)
            console.print(f"[green]Generated {len(glossary)} glossary entries[/green]")

    # Translate book metadata if not already done
    progress = BookProgress.load(book_dir)
    if progress and not progress.title_vi:
        console.print("[blue]Translating book metadata...[/blue]")
        llm = LLMClient(task="translate")
        
        # Translate book title
        if progress.title:
            progress.title_vi = await llm.translate_title(progress.title, "book")
            console.print(f"  Title: {progress.title} → {progress.title_vi}")
        
        # Translate author name
        if progress.author:
            progress.author_vi = await llm.translate_title(progress.author, "author")
            console.print(f"  Author: {progress.author} → {progress.author_vi}")
        
        progress.save(book_dir)

    # Initialize TF-IDF scorer for intelligent glossary selection
    term_scorer = None
    if len(glossary) > 0:
        from dich_truyen.translator.term_scorer import SimpleTermScorer
        
        console.print("[dim]Initializing TF-IDF scorer for glossary selection...[/dim]")
        
        # Read all chapter contents for IDF calculation
        raw_dir = book_dir / "raw"
        all_files = sorted(raw_dir.glob("*.txt"))
        documents = []
        for txt_file in all_files:
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    documents.append(f.read())
            except Exception:
                pass  # Skip files that can't be read
        
        if documents:
            # Extract glossary terms
            terms = [entry.chinese for entry in glossary.entries]
            
            # Fit the scorer
            term_scorer = SimpleTermScorer()
            term_scorer.fit(documents, terms)
            
            console.print(f"[dim]  TF-IDF scorer fitted with {len(documents)} chapters, {len(terms)} terms[/dim]")

    return TranslationEngine(
        style=style,
        glossary=glossary,
        term_scorer=term_scorer,
    )


async def translate_chapter_titles(book_dir: Path, chapters_spec: Optional[str] = None) -> None:
    """Translate chapter titles for a book.

    Args:
        book_dir: Book directory path
        chapters_spec: Optional chapter range
    """
    from dich_truyen.utils.progress import parse_chapter_range
    
    book_dir = Path(book_dir)
    progress = BookProgress.load(book_dir)
    if not progress:
        raise ValueError(f"Book not initialized: {book_dir}")

    # Apply chapter range filter if specified
    all_chapters = progress.chapters
    max_chapter = len(all_chapters)
    
    if chapters_spec:
        indices = parse_chapter_range(chapters_spec, max_chapter)
        chapters_to_translate = [c for c in all_chapters if c.index in indices and not c.title_vi]
    else:
        chapters_to_translate = [c for c in all_chapters if not c.title_vi]

    if not chapters_to_translate:
        console.print("[green]All chapter titles already translated![/green]")
        return

    console.print(f"[blue]Translating {len(chapters_to_translate)} chapter titles...[/blue]")
    
    llm = LLMClient(task="translate")
    
    for chapter in chapters_to_translate:
        if chapter.title_cn:
            chapter.title_vi = await llm.translate_title(chapter.title_cn, "chapter")
            console.print(f"[dim]  Ch.{chapter.index}: {chapter.title_cn} → {chapter.title_vi}[/dim]")
    
    progress.save(book_dir)
    console.print("[green]Chapter titles translated![/green]")
