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


class ChapterDetail(BaseModel):
    """Chapter info for book detail view."""

    index: int
    id: str
    title_cn: str
    title_vi: Optional[str] = None
    status: str
    has_raw: bool = False
    has_translated: bool = False


class BookDetail(BaseModel):
    """Full book detail."""

    id: str
    title: str
    title_vi: str
    author: str
    author_vi: str
    url: str
    encoding: str
    chapters: list[ChapterDetail]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChapterContent(BaseModel):
    """Chapter text content."""

    chapter_index: int
    content: str


def _find_chapter_file(directory: Path, chapter_index: int) -> Optional[Path]:
    """Find chapter file using dual-pattern lookup.

    Matches the existing logic in formatter/assembler.py:
    1. Try new pattern: {index}.txt
    2. Fall back to old pattern: {index:04d}_*.txt (glob)

    Returns:
        Path to file if found, None otherwise.
    """
    if not directory.exists():
        return None
    # New pattern first
    new_pattern = directory / f"{chapter_index}.txt"
    if new_pattern.exists():
        return new_pattern
    # Old pattern with glob
    old_pattern = f"{chapter_index:04d}_*.txt"
    files = list(directory.glob(old_pattern))
    return files[0] if files else None


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: str) -> BookDetail:
    """Get book detail with chapter list."""
    book_dir = _books_dir / book_id
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail="Book not found")

    progress = BookProgress.load(book_dir)
    if progress is None:
        raise HTTPException(status_code=404, detail="Book not found")

    raw_dir = book_dir / "raw"
    translated_dir = book_dir / "translated"

    chapters = []
    for ch in progress.chapters:
        has_raw = _find_chapter_file(raw_dir, ch.index) is not None
        has_translated = _find_chapter_file(translated_dir, ch.index) is not None
        chapters.append(ChapterDetail(
            index=ch.index,
            id=ch.id,
            title_cn=ch.title_cn,
            title_vi=ch.title_vi,
            status=ch.status.value,
            has_raw=has_raw,
            has_translated=has_translated,
        ))

    return BookDetail(
        id=book_id,
        title=progress.title,
        title_vi=progress.title_vi,
        author=progress.author,
        author_vi=progress.author_vi,
        url=progress.url,
        encoding=progress.encoding,
        chapters=chapters,
        created_at=str(progress.created_at) if progress.created_at else None,
        updated_at=str(progress.updated_at) if progress.updated_at else None,
    )


@router.get("/{book_id}/chapters/{chapter_num}/raw", response_model=ChapterContent)
async def get_chapter_raw(book_id: str, chapter_num: int) -> ChapterContent:
    """Get raw Chinese chapter content."""
    file_path = _find_chapter_file(_books_dir / book_id / "raw", chapter_num)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    content = file_path.read_text(encoding="utf-8")
    return ChapterContent(chapter_index=chapter_num, content=content)


@router.get("/{book_id}/chapters/{chapter_num}/translated", response_model=ChapterContent)
async def get_chapter_translated(book_id: str, chapter_num: int) -> ChapterContent:
    """Get translated Vietnamese chapter content."""
    file_path = _find_chapter_file(_books_dir / book_id / "translated", chapter_num)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    content = file_path.read_text(encoding="utf-8")
    return ChapterContent(chapter_index=chapter_num, content=content)

