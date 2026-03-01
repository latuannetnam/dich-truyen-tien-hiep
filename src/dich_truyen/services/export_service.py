"""ExportService — business logic for book export operations.

Wraps DirectEPUBAssembler and CalibreExporter behind a clean interface
suitable for REST endpoints and future CLI refactoring.
"""

from pathlib import Path
from typing import Any

from dich_truyen.exporter.calibre import CalibreExporter, export_book


class ExportService:
    """Manage book export operations.

    Provides a dict-based API over the exporter modules so route handlers
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

    async def export(
        self,
        book_id: str,
        output_format: str = "epub",
    ) -> dict[str, Any]:
        """Export a book to the specified format.

        Args:
            book_id: Book directory name.
            output_format: Target format (epub, azw3, mobi, pdf).

        Returns:
            Dict with 'success', 'output_path', and optionally 'error_message'.
        """
        book_dir = self._resolve_book_dir(book_id)
        result = await export_book(book_dir, output_format)
        return result.model_dump()

    def get_supported_formats(self) -> list[str]:
        """Return list of supported output formats."""
        return CalibreExporter.SUPPORTED_FORMATS

    def get_export_status(self, book_id: str) -> dict[str, Any]:
        """Check what export outputs exist for a book.

        Returns:
            Dict with 'formats' mapping format name to output path if it exists.
        """
        book_dir = self._resolve_book_dir(book_id)
        output_dir = book_dir / "output"
        existing: dict[str, str] = {}

        if output_dir.exists():
            for fmt in CalibreExporter.SUPPORTED_FORMATS:
                matches = list(output_dir.glob(f"*.{fmt}"))
                if matches:
                    existing[fmt] = str(matches[0])

        return {"formats": existing}
