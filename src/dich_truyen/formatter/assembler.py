"""HTML assembler for creating book from translated chapters."""

from pathlib import Path
from typing import Optional

from rich.console import Console

from dich_truyen.formatter.metadata import BookMetadataManager
from dich_truyen.utils.progress import BookProgress, Chapter

console = Console()

# HTML template for the book
BOOK_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {meta_tags}
    <style>
        body {{
            font-family: 'Noto Serif', 'Times New Roman', serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 10px;
            color: #1a1a1a;
        }}
        .book-info {{
            text-align: center;
            margin-bottom: 30px;
            color: #666;
        }}
        .toc {{
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 5px;
        }}
        .toc h2 {{
            margin-top: 0;
        }}
        .toc-item {{
            margin: 8px 0;
        }}
        .toc-item a {{
            color: #2563eb;
            text-decoration: none;
        }}
        .toc-item a:hover {{
            text-decoration: underline;
        }}
        .chapter {{
            page-break-before: always;
            margin-top: 40px;
        }}
        .chapter-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin: 30px 0 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e5e5;
        }}
        .chapter-content {{
            text-align: justify;
        }}
        .chapter-content p {{
            margin: 1em 0;
            text-indent: 2em;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="book-info">
        <p>Tác giả: {author}</p>
        <p>Dịch giả: {translator}</p>
    </div>
    
    <div class="toc">
        <h2>Mục Lục</h2>
{toc_content}
    </div>
    
{chapters_content}

</body>
</html>
"""

TOC_ITEM_TEMPLATE = '        <div class="toc-item"><a href="#chapter-{index}">{title}</a></div>'

CHAPTER_TEMPLATE = """
    <div class="chapter" id="chapter-{index}">
        <h2 class="chapter-title">{title}</h2>
        <div class="chapter-content">
{content}
        </div>
    </div>
"""


class HTMLAssembler:
    """Assemble translated chapters into HTML book."""

    def __init__(self, book_dir: Path):
        """Initialize the HTML assembler.

        Args:
            book_dir: Book directory path
        """
        self.book_dir = Path(book_dir)
        self.translated_dir = self.book_dir / "translated"
        self.formatted_dir = self.book_dir / "formatted"
        self.progress: Optional[BookProgress] = None
        self.metadata: Optional[BookMetadataManager] = None

    def load_book_data(self) -> None:
        """Load book progress and metadata."""
        self.progress = BookProgress.load(self.book_dir)
        if not self.progress:
            raise ValueError(f"Book not initialized: {self.book_dir}")

        self.metadata = BookMetadataManager.from_book_progress(self.progress)

    def get_translated_chapters(self) -> list[tuple[Chapter, Path]]:
        """Get list of translated chapters with their file paths.

        Returns:
            List of (chapter, file_path) tuples
        """
        if not self.progress:
            self.load_book_data()

        chapters_with_files = []

        for chapter in self.progress.chapters:
            # Find the translated file
            pattern = f"{chapter.index:04d}_*.txt"
            files = list(self.translated_dir.glob(pattern))
            if files:
                chapters_with_files.append((chapter, files[0]))

        return chapters_with_files

    def read_chapter_content(self, file_path: Path) -> str:
        """Read and format chapter content.

        Args:
            file_path: Path to chapter file

        Returns:
            Formatted HTML content
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Skip the first line if it's a title (starts with #)
        lines = content.split("\n")
        if lines and lines[0].startswith("#"):
            lines = lines[1:]

        content = "\n".join(lines).strip()

        # Convert paragraphs to HTML
        paragraphs = content.split("\n\n")
        html_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if para:
                # Replace single newlines with spaces within paragraphs
                para = " ".join(para.split("\n"))
                html_paragraphs.append(f"            <p>{para}</p>")

        return "\n".join(html_paragraphs)

    def get_chapter_title(self, chapter: Chapter, file_path: Path) -> str:
        """Get the chapter title.

        Args:
            chapter: Chapter object
            file_path: Path to chapter file

        Returns:
            Chapter title
        """
        # First try to get from chapter object
        if chapter.title_vi:
            return chapter.title_vi

        # Try to extract from file
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line.startswith("#"):
                return first_line.lstrip("#").strip()

        # Fall back to Chinese title
        return chapter.title_cn or f"Chương {chapter.index}"

    def generate_toc(self, chapters: list[tuple[Chapter, Path]]) -> str:
        """Generate table of contents HTML.

        Args:
            chapters: List of (chapter, file_path) tuples

        Returns:
            TOC HTML string
        """
        toc_items = []
        for chapter, file_path in chapters:
            title = self.get_chapter_title(chapter, file_path)
            item = TOC_ITEM_TEMPLATE.format(index=chapter.index, title=title)
            toc_items.append(item)

        return "\n".join(toc_items)

    def format_chapter(self, chapter: Chapter, file_path: Path) -> str:
        """Format a single chapter as HTML.

        Args:
            chapter: Chapter object
            file_path: Path to chapter file

        Returns:
            Formatted chapter HTML
        """
        title = self.get_chapter_title(chapter, file_path)
        content = self.read_chapter_content(file_path)

        return CHAPTER_TEMPLATE.format(
            index=chapter.index,
            title=title,
            content=content,
        )

    def assemble(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        translator: Optional[str] = None,
    ) -> Path:
        """Assemble the full book HTML.

        Args:
            title: Override book title
            author: Override author name
            translator: Override translator name

        Returns:
            Path to the generated HTML file
        """
        # Load book data
        self.load_book_data()

        # Override metadata if provided
        if title:
            self.metadata.title = title
        if author:
            self.metadata.author = author
        if translator:
            self.metadata.translator = translator

        # Get translated chapters
        chapters = self.get_translated_chapters()

        if not chapters:
            raise ValueError("No translated chapters found")

        console.print(f"[blue]Assembling {len(chapters)} chapters...[/blue]")

        # Generate TOC
        toc_content = self.generate_toc(chapters)

        # Generate chapters content
        chapters_html = []
        for chapter, file_path in chapters:
            chapter_html = self.format_chapter(chapter, file_path)
            chapters_html.append(chapter_html)

        chapters_content = "\n".join(chapters_html)

        # Assemble the full HTML
        html = BOOK_HTML_TEMPLATE.format(
            title=self.metadata.title,
            meta_tags=self.metadata.to_html_meta(),
            author=self.metadata.author,
            translator=self.metadata.translator,
            toc_content=toc_content,
            chapters_content=chapters_content,
        )

        # Ensure output directory exists
        self.formatted_dir.mkdir(exist_ok=True)

        # Save the HTML file
        output_path = self.formatted_dir / "book.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        # Update progress metadata
        self.metadata.update_progress(self.progress)
        self.progress.save(self.book_dir)

        console.print(f"[green]Book assembled: {output_path}[/green]")

        return output_path


async def format_book(
    book_dir: Path,
    title: Optional[str] = None,
    author: Optional[str] = None,
    translator: Optional[str] = None,
    cover: Optional[Path] = None,
) -> Path:
    """Format a book from translated chapters.

    Args:
        book_dir: Book directory path
        title: Override book title
        author: Override author name
        translator: Override translator name
        cover: Cover image path

    Returns:
        Path to the generated HTML file
    """
    assembler = HTMLAssembler(book_dir)

    # Handle cover image
    if cover:
        # Copy cover to book directory
        import shutil
        dest_cover = book_dir / "cover" / cover.name
        dest_cover.parent.mkdir(exist_ok=True)
        shutil.copy(cover, dest_cover)

        # Update metadata
        assembler.load_book_data()
        assembler.metadata.cover_path = str(dest_cover)

    return assembler.assemble(title=title, author=author, translator=translator)
