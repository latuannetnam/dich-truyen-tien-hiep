"""Book listing and detail API routes."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dich_truyen.utils.progress import BookProgress, ChapterStatus


router = APIRouter(prefix="/api/v1/books", tags=["books"])

# Set by server.py at startup
_books_dir: Path = Path("books")


def set_books_dir(books_dir: Path) -> None:
    """Set the books directory path."""
    global _books_dir
    _books_dir = books_dir


class BookSummary(BaseModel):
    """Book summary for list view."""

    id: str
    title: str
    title_vi: str
    author: str
    author_vi: str
    url: str
    total_chapters: int
    pending_chapters: int
    crawled_chapters: int
    translated_chapters: int
    formatted_chapters: int
    exported_chapters: int
    error_chapters: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("", response_model=list[BookSummary])
async def list_books() -> list[BookSummary]:
    """List all books with summary stats."""
    books: list[BookSummary] = []

    if not _books_dir.exists():
        return books

    for book_dir in sorted(_books_dir.iterdir()):
        book_json = book_dir / "book.json"
        if not book_json.exists():
            continue

        progress = BookProgress.load(book_dir)
        if progress is None:
            continue

        status_counts = {s: 0 for s in ChapterStatus}
        for ch in progress.chapters:
            status_counts[ch.status] += 1

        books.append(BookSummary(
            id=book_dir.name,
            title=progress.title,
            title_vi=progress.title_vi,
            author=progress.author,
            author_vi=progress.author_vi,
            url=progress.url,
            total_chapters=len(progress.chapters),
            pending_chapters=status_counts[ChapterStatus.PENDING],
            crawled_chapters=status_counts[ChapterStatus.CRAWLED],
            translated_chapters=status_counts[ChapterStatus.TRANSLATED],
            formatted_chapters=status_counts.get(ChapterStatus.FORMATTED, 0),
            exported_chapters=status_counts.get(ChapterStatus.EXPORTED, 0),
            error_chapters=status_counts[ChapterStatus.ERROR],
            created_at=str(progress.created_at) if progress.created_at else None,
            updated_at=str(progress.updated_at) if progress.updated_at else None,
        ))

    return books
