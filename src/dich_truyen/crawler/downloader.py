"""Chapter downloader with progress tracking and resume support."""

import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from dich_truyen.config import CrawlerConfig, get_config
from dich_truyen.crawler.base import BaseCrawler
from dich_truyen.crawler.pattern import DiscoveredChapter, PatternDiscovery
from dich_truyen.utils.progress import (
    BookPatterns,
    BookProgress,
    Chapter,
    ChapterStatus,
    parse_chapter_range,
)

console = Console()


class DownloadResult(BaseModel):
    """Result of download operation."""

    total: int
    downloaded: int
    skipped: int
    failed: int
    errors: list[str] = []


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    # Remove non-alphanumeric characters (keeping Chinese)
    text = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", text)
    # Replace spaces with hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Remove leading/trailing hyphens
    text = text.strip("-")
    return text.lower()[:50] if text else "unknown-book"


class ChapterDownloader:
    """Download chapters with progress tracking and resume support."""

    def __init__(
        self,
        book_dir: Path,
        config: Optional[CrawlerConfig] = None,
    ):
        """Initialize the downloader.

        Args:
            book_dir: Directory to store book data
            config: Crawler configuration
        """
        self.book_dir = Path(book_dir)
        self.config = config or get_config().crawler
        self.raw_dir = self.book_dir / "raw"

        # Ensure directories exist
        self.book_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(exist_ok=True)

    async def initialize_book(
        self,
        url: str,
        encoding: Optional[str] = None,
    ) -> BookProgress:
        """Initialize a book from its index URL.

        Args:
            url: Book index page URL
            encoding: Optional explicit encoding

        Returns:
            BookProgress with discovered info and chapters
        """
        # Load existing progress or create new
        progress = BookProgress.load_or_create(self.book_dir, url)

        # If already initialized with chapters, return existing
        if progress.chapters:
            console.print(f"[green]Loaded existing book: {progress.title}[/green]")
            console.print(f"  Chapters: {len(progress.chapters)}")
            return progress

        console.print(f"[blue]Analyzing book URL: {url}[/blue]")

        # Fetch the index page
        async with BaseCrawler(self.config) as crawler:
            html = await crawler.fetch(url, encoding)

            # Auto-detect encoding if not specified
            if encoding is None:
                from dich_truyen.utils.encoding import detect_encoding

                raw_content = await crawler.fetch_raw(url)
                encoding = detect_encoding(raw_content)

        # Discover book information using LLM
        discovery = PatternDiscovery()
        discovered = await discovery.analyze_index_page(html, url)

        console.print(f"[green]Discovered book: {discovered.title}[/green]")
        console.print(f"  Author: {discovered.author}")
        console.print(f"  Encoding: {encoding or discovered.encoding}")

        # Extract chapters using discovered pattern
        chapters = discovery.extract_chapters_from_html(
            html, url, discovered.patterns.chapter_selector
        )

        console.print(f"  Found {len(chapters)} chapters")

        # Analyze chapter page structure
        if chapters:
            console.print("[blue]Analyzing chapter page structure...[/blue]")
            async with BaseCrawler(self.config) as crawler:
                chapter_html = await crawler.fetch(chapters[0].url, encoding)
                content_patterns = await discovery.analyze_chapter_page(chapter_html, chapters[0].url)

            # Merge patterns
            discovered.patterns.title_selector = content_patterns.title_selector
            discovered.patterns.content_selector = content_patterns.content_selector
            discovered.patterns.elements_to_remove = content_patterns.elements_to_remove

        # Update progress
        progress.title = discovered.title
        progress.author = discovered.author
        progress.encoding = encoding or discovered.encoding
        progress.patterns = discovered.patterns
        progress.chapters = [
            Chapter(
                index=ch.index,
                id=ch.id,
                title_cn=ch.title,
                url=ch.url,
                status=ChapterStatus.PENDING,
            )
            for ch in chapters
        ]

        # Save progress
        progress.save(self.book_dir)
        console.print(f"[green]Book initialized: {self.book_dir}[/green]")

        return progress

    async def download_chapters(
        self,
        chapters_spec: Optional[str] = None,
        resume: bool = True,
    ) -> DownloadResult:
        """Download chapters from the book.

        Args:
            chapters_spec: Optional chapter range (e.g., "1-100" or "1,5,10-20")
            resume: Whether to skip already downloaded chapters

        Returns:
            Download result with statistics
        """
        progress = BookProgress.load(self.book_dir)
        if not progress:
            raise ValueError(f"Book not initialized. Run initialize_book first: {self.book_dir}")

        # Determine which chapters to download
        all_chapters = progress.chapters
        max_chapter = len(all_chapters)

        if chapters_spec:
            indices = parse_chapter_range(chapters_spec, max_chapter)
            chapters_to_process = [c for c in all_chapters if c.index in indices]
        else:
            chapters_to_process = all_chapters

        # Filter already downloaded if resuming
        if resume:
            chapters_to_download = [
                c for c in chapters_to_process if c.status == ChapterStatus.PENDING
            ]
            skipped = len(chapters_to_process) - len(chapters_to_download)
        else:
            chapters_to_download = chapters_to_process
            skipped = 0

        if not chapters_to_download:
            console.print("[green]All chapters already downloaded![/green]")
            return DownloadResult(
                total=len(chapters_to_process),
                downloaded=0,
                skipped=len(chapters_to_process),
                failed=0,
            )

        console.print(f"[blue]Downloading {len(chapters_to_download)} chapters...[/blue]")
        if skipped > 0:
            console.print(f"  Skipping {skipped} already downloaded")

        # Create extraction discovery
        discovery = PatternDiscovery()

        result = DownloadResult(
            total=len(chapters_to_process),
            downloaded=0,
            skipped=skipped,
            failed=0,
        )

        # Download with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as pbar:
            task = pbar.add_task("Downloading", total=len(chapters_to_download))

            async with BaseCrawler(self.config) as crawler:
                for chapter in chapters_to_download:
                    pbar.update(task, description=f"Ch.{chapter.index}: {chapter.title_cn[:20]}...")

                    try:
                        # Fetch chapter page
                        html = await crawler.fetch(chapter.url, progress.encoding)

                        # Extract content
                        title, content = discovery.extract_chapter_content(html, progress.patterns)

                        # Update title if extracted
                        if title and not chapter.title_cn:
                            chapter.title_cn = title

                        # Save to file
                        filename = f"{chapter.index:04d}_{slugify(chapter.title_cn)}.txt"
                        filepath = self.raw_dir / filename

                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(f"# {chapter.title_cn}\n\n")
                            f.write(content)

                        # Update status
                        progress.update_chapter_status(chapter.index, ChapterStatus.CRAWLED)
                        result.downloaded += 1

                    except Exception as e:
                        error_msg = f"Chapter {chapter.index}: {str(e)}"
                        result.errors.append(error_msg)
                        result.failed += 1
                        progress.update_chapter_status(
                            chapter.index, ChapterStatus.ERROR, str(e)
                        )
                        console.print(f"[red]Error: {error_msg}[/red]")

                    # Save progress periodically
                    if result.downloaded % 10 == 0:
                        progress.save(self.book_dir)

                    # Rate limiting
                    await crawler.delay()
                    pbar.advance(task)

        # Final save
        progress.save(self.book_dir)

        console.print(f"\n[green]Download complete![/green]")
        console.print(f"  Downloaded: {result.downloaded}")
        console.print(f"  Skipped: {result.skipped}")
        console.print(f"  Failed: {result.failed}")

        return result


async def create_book_directory(url: str, base_dir: Path = Path("books")) -> Path:
    """Create a unique book directory from URL.

    Args:
        url: Book index URL
        base_dir: Base directory for all books

    Returns:
        Path to the book directory
    """
    # Extract a slug from the URL path
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")

    # Try to get a meaningful name from the path
    if path_parts:
        slug = "-".join(path_parts[-2:]) if len(path_parts) >= 2 else path_parts[-1]
        slug = re.sub(r"[^\w-]", "", slug)
    else:
        slug = "unknown-book"

    book_dir = base_dir / slug
    book_dir.mkdir(parents=True, exist_ok=True)

    return book_dir
