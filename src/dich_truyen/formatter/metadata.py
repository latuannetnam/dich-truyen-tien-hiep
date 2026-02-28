"""Book metadata management for formatting and export."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from dich_truyen.utils.progress import BookProgress


class BookMetadataManager(BaseModel):
    """Book metadata for formatting and export."""

    title: str = Field(description="Vietnamese book title")
    title_original: str = Field(default="", description="Original Chinese title")
    author: str = Field(description="Author name")
    translator: str = Field(default="AI Translator", description="Translator name")
    description: str = Field(default="", description="Book description/synopsis")
    cover_path: Optional[str] = Field(default=None, description="Path to cover image")
    language: str = Field(default="vi", description="Book language code")

    @classmethod
    def from_book_progress(cls, progress: BookProgress) -> "BookMetadataManager":
        """Create metadata from book progress.

        Args:
            progress: Book progress data

        Returns:
            BookMetadataManager instance
        """
        return cls(
            title=progress.title_vi or progress.title,
            title_original=progress.title,
            # Use translated author name if available
            author=progress.author_vi or progress.author,
            translator=progress.metadata.translator,
            description=progress.metadata.description,
            cover_path=progress.metadata.cover_path,
        )

    @classmethod
    def load_from_book_dir(cls, book_dir: Path) -> Optional["BookMetadataManager"]:
        """Load metadata from book directory.

        Args:
            book_dir: Book directory path

        Returns:
            BookMetadataManager if book.json exists
        """
        progress = BookProgress.load(book_dir)
        if progress:
            return cls.from_book_progress(progress)
        return None

    def update_progress(self, progress: BookProgress) -> None:
        """Update book progress with this metadata.

        Args:
            progress: Book progress to update
        """
        progress.title_vi = self.title
        progress.metadata.translator = self.translator
        progress.metadata.description = self.description
        progress.metadata.cover_path = self.cover_path

    def to_calibre_args(self) -> list[str]:
        """Convert metadata to Calibre ebook-convert arguments.

        Returns:
            List of command-line arguments
        """
        args = [
            "--title", self.title,
            "--authors", self.author,
            "--language", self.language,
        ]

        if self.description:
            args.extend(["--comments", self.description])

        if self.cover_path:
            args.extend(["--cover", self.cover_path])

        return args

    def to_html_meta(self) -> str:
        """Generate HTML meta tags.

        Returns:
            HTML meta tags string
        """
        lines = [
            f'<meta name="author" content="{self.author}">',
            f'<meta name="translator" content="{self.translator}">',
            f'<meta name="language" content="{self.language}">',
        ]
        if self.description:
            desc = self.description.replace('"', "&quot;")
            lines.append(f'<meta name="description" content="{desc}">')
        return "\n    ".join(lines)
