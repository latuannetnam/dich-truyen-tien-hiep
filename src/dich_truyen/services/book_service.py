"""BookService — business logic for book file operations.

Wraps BookProgress behind a clean interface suitable for REST endpoints
and future CLI refactoring.
"""

from pathlib import Path
from typing import Any

from dich_truyen.utils.progress import BookProgress, ChapterStatus


class BookService:
    """Manage book metadata and chapter status.

    Provides a dict-based API over BookProgress so route handlers
    stay thin and logic can be tested without HTTP.
    """

    def __init__(self, books_dir: Path) -> None:
        self._books_dir = books_dir

    def _resolve_book_dir(self, book_id: str) -> Path:
        """Get book directory, raising ValueError if not found."""
        book_dir = self._books_dir / book_id
        if not book_dir.exists():
            raise ValueError(f"Book not found: {book_id}")
        return book_dir

    def list_books(self) -> list[dict[str, Any]]:
        """List all books with summary info.

        Returns:
            List of dicts with book id, title, author, progress stats.
        """
        books: list[dict[str, Any]] = []
        if not self._books_dir.exists():
            return books

        for book_dir in sorted(self._books_dir.iterdir()):
            if not book_dir.is_dir():
                continue
            progress = BookProgress.load(book_dir)
            if progress is None:
                continue

            total = len(progress.chapters)
            translated = sum(
                1
                for c in progress.chapters
                if c.status
                in (
                    ChapterStatus.TRANSLATED,
                    ChapterStatus.FORMATTED,
                    ChapterStatus.EXPORTED,
                )
            )
            books.append(
                {
                    "id": book_dir.name,
                    "title": progress.title,
                    "title_vi": progress.title_vi,
                    "author": progress.author,
                    "author_vi": progress.author_vi,
                    "total_chapters": total,
                    "translated_chapters": translated,
                }
            )
        return books

    def get_book(self, book_id: str) -> dict[str, Any]:
        """Get full book details including chapter list.

        Args:
            book_id: Book directory name.

        Returns:
            Dict with book metadata and chapters.

        Raises:
            ValueError: If book not found or has no progress file.
        """
        book_dir = self._resolve_book_dir(book_id)
        progress = BookProgress.load(book_dir)
        if progress is None:
            raise ValueError(f"No progress file for book: {book_id}")

        return {
            "id": book_dir.name,
            "url": progress.url,
            "title": progress.title,
            "title_vi": progress.title_vi,
            "author": progress.author,
            "author_vi": progress.author_vi,
            "encoding": progress.encoding,
            "chapters": [
                {
                    "index": c.index,
                    "title_cn": c.title_cn,
                    "title_vi": c.title_vi,
                    "status": c.status.value,
                    "url": c.url,
                }
                for c in progress.chapters
            ],
        }

    def get_chapter_content(self, book_id: str, chapter_index: int) -> dict[str, str]:
        """Read translated and/or raw content for a chapter.

        Returns:
            Dict with 'translated' and 'raw' content strings (empty if missing).
        """
        book_dir = self._resolve_book_dir(book_id)

        translated = ""
        raw = ""

        translated_path = book_dir / "translated" / f"chapter_{chapter_index:04d}.txt"
        if translated_path.exists():
            translated = translated_path.read_text(encoding="utf-8")

        raw_path = book_dir / "raw" / f"chapter_{chapter_index:04d}.txt"
        if raw_path.exists():
            raw = raw_path.read_text(encoding="utf-8")

        return {"translated": translated, "raw": raw}
