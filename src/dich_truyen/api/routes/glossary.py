"""Glossary API routes — CRUD for book glossaries.

Note: Uses _load_glossary_quiet() instead of Glossary.load_or_create()
to avoid Glossary.from_csv()'s logger.info() on every request.
This ensures the server log stays clean while CLI behavior is unchanged.
"""

import csv
import io
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dich_truyen.translator.glossary import Glossary, GlossaryEntry

router = APIRouter(prefix="/api/v1/books/{book_id}/glossary", tags=["glossary"])

_books_dir: Path = Path("books")


def set_books_dir(books_dir: Path) -> None:
    """Set the books directory path."""
    global _books_dir
    _books_dir = books_dir


def _get_book_dir(book_id: str) -> Path:
    """Get book directory, raising 404 if not found."""
    book_dir = _books_dir / book_id
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail="Book not found")
    return book_dir


def _load_glossary_quiet(book_dir: Path) -> Glossary:
    """Load glossary without log noise.

    Glossary.from_csv() emits logger.info("glossary_imported"),
    which is fine for CLI but noisy for the API server. This
    reads the CSV directly and constructs a Glossary silently.
    """
    glossary_path = book_dir / "glossary.csv"
    if not glossary_path.exists():
        return Glossary()

    entries: list[GlossaryEntry] = []
    with open(glossary_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(
                GlossaryEntry(
                    chinese=row["chinese"],
                    vietnamese=row["vietnamese"],
                    category=row.get("category", "general"),
                    notes=row.get("notes") or None,
                )
            )
    return Glossary(entries)


class GlossaryEntryRequest(BaseModel):
    """Request body for adding/updating a glossary entry."""

    chinese: str
    vietnamese: str
    category: str = "general"
    notes: Optional[str] = None


class GlossaryResponse(BaseModel):
    """Response with glossary entries."""

    entries: list[dict[str, Any]]
    total: int
    categories: list[str]


@router.get("", response_model=GlossaryResponse)
async def get_glossary(book_id: str) -> GlossaryResponse:
    """Get all glossary entries for a book."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)
    entries = [
        {
            "chinese": e.chinese,
            "vietnamese": e.vietnamese,
            "category": e.category,
            "notes": e.notes,
        }
        for e in glossary.entries
    ]
    return GlossaryResponse(
        entries=entries,
        total=len(entries),
        categories=Glossary.CATEGORIES,
    )


@router.post("")
async def add_glossary_entry(
    book_id: str, entry: GlossaryEntryRequest
) -> dict[str, str]:
    """Add or update a glossary entry."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)
    glossary.add(GlossaryEntry(
        chinese=entry.chinese,
        vietnamese=entry.vietnamese,
        category=entry.category,
        notes=entry.notes,
    ))
    glossary.save(book_dir)
    return {"status": "ok"}


@router.put("/{term}")
async def update_glossary_entry(
    book_id: str, term: str, entry: GlossaryEntryRequest
) -> dict[str, str]:
    """Update an existing glossary entry."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)

    # Remove old entry if Chinese term changed
    if term != entry.chinese:
        glossary.remove(term)

    glossary.add(GlossaryEntry(
        chinese=entry.chinese,
        vietnamese=entry.vietnamese,
        category=entry.category,
        notes=entry.notes,
    ))
    glossary.save(book_dir)
    return {"status": "ok"}


@router.delete("/{term}")
async def delete_glossary_entry(book_id: str, term: str) -> dict[str, str]:
    """Delete a glossary entry by Chinese term."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)
    if not glossary.remove(term):
        raise HTTPException(status_code=404, detail="Term not found")
    glossary.save(book_dir)
    return {"status": "ok"}


@router.get("/export")
async def export_glossary_csv(book_id: str) -> StreamingResponse:
    """Export glossary as CSV download."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["chinese", "vietnamese", "category", "notes"])
    for entry in glossary.entries:
        writer.writerow([entry.chinese, entry.vietnamese, entry.category, entry.notes or ""])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={book_id}_glossary.csv"},
    )


@router.post("/import")
async def import_glossary_csv(
    book_id: str, file: UploadFile = File(...)
) -> dict[str, Any]:
    """Import glossary entries from uploaded CSV."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    for row in reader:
        if "chinese" in row and "vietnamese" in row:
            glossary.add(GlossaryEntry(
                chinese=row["chinese"],
                vietnamese=row["vietnamese"],
                category=row.get("category", "general"),
                notes=row.get("notes"),
            ))
            imported += 1

    glossary.save(book_dir)
    return {"status": "ok", "imported": imported, "total": len(glossary)}
