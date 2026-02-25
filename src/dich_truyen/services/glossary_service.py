"""GlossaryService — business logic for glossary CRUD.

Consolidates glossary operations behind a clean interface so the route
handler stays thin and the logic can be tested without HTTP.
"""

import csv
import io
from pathlib import Path
from typing import Any, Optional

from dich_truyen.translator.glossary import Glossary, GlossaryEntry


class GlossaryService:
    """Manage glossary read/write for a book directory.

    Uses quiet loading to avoid Rich console output on every API request.
    """

    def __init__(self, books_dir: Path) -> None:
        self._books_dir = books_dir

    def _resolve_book_dir(self, book_id: str) -> Path:
        """Get book directory, raising ValueError if not found."""
        book_dir = self._books_dir / book_id
        if not book_dir.exists():
            raise ValueError(f"Book not found: {book_id}")
        return book_dir

    def _load_quiet(self, book_dir: Path) -> Glossary:
        """Load glossary from CSV without Rich console output."""
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

    def get_glossary(self, book_id: str) -> dict[str, Any]:
        """Return glossary entries for a book."""
        book_dir = self._resolve_book_dir(book_id)
        glossary = self._load_quiet(book_dir)
        entries = [
            {
                "chinese": e.chinese,
                "vietnamese": e.vietnamese,
                "category": e.category,
                "notes": e.notes,
            }
            for e in glossary.entries
        ]
        return {
            "entries": entries,
            "total": len(entries),
            "categories": Glossary.CATEGORIES,
        }

    def add_entry(
        self,
        book_id: str,
        chinese: str,
        vietnamese: str,
        category: str = "general",
        notes: Optional[str] = None,
    ) -> None:
        """Add or update a glossary entry."""
        book_dir = self._resolve_book_dir(book_id)
        glossary = self._load_quiet(book_dir)
        glossary.add(
            GlossaryEntry(
                chinese=chinese,
                vietnamese=vietnamese,
                category=category,
                notes=notes,
            )
        )
        glossary.save(book_dir)

    def remove_entry(self, book_id: str, term: str) -> bool:
        """Remove entry by Chinese term. Returns True if removed."""
        book_dir = self._resolve_book_dir(book_id)
        glossary = self._load_quiet(book_dir)
        removed = glossary.remove(term)
        if removed:
            glossary.save(book_dir)
        return removed

    def export_csv(self, book_id: str) -> str:
        """Export glossary as CSV string."""
        book_dir = self._resolve_book_dir(book_id)
        glossary = self._load_quiet(book_dir)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["chinese", "vietnamese", "category", "notes"])
        for entry in glossary.entries:
            writer.writerow(
                [entry.chinese, entry.vietnamese, entry.category, entry.notes or ""]
            )
        return output.getvalue()

    def import_csv(self, book_id: str, csv_text: str) -> int:
        """Import entries from CSV text. Returns count imported."""
        book_dir = self._resolve_book_dir(book_id)
        glossary = self._load_quiet(book_dir)

        reader = csv.DictReader(io.StringIO(csv_text))
        imported = 0
        for row in reader:
            if "chinese" in row and "vietnamese" in row:
                glossary.add(
                    GlossaryEntry(
                        chinese=row["chinese"],
                        vietnamese=row["vietnamese"],
                        category=row.get("category", "general"),
                        notes=row.get("notes"),
                    )
                )
                imported += 1

        glossary.save(book_dir)
        return imported
