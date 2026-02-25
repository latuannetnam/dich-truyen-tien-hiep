"""Export API routes — book export and download."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from dich_truyen.services.export_service import ExportService

router = APIRouter(prefix="/api/v1", tags=["export"])

_export_service: ExportService | None = None


def set_export_service(service: ExportService) -> None:
    """Set the export service instance."""
    global _export_service
    _export_service = service


def _get_service() -> ExportService:
    if _export_service is None:
        raise RuntimeError("ExportService not initialized")
    return _export_service


@router.get("/export/formats")
async def get_supported_formats() -> list[str]:
    """Get list of supported export formats."""
    return _get_service().get_supported_formats()


@router.get("/books/{book_id}/export")
async def get_export_status(book_id: str) -> dict[str, Any]:
    """Get export status for a book."""
    try:
        return _get_service().get_export_status(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/books/{book_id}/export")
async def start_export(book_id: str, format: str = "epub") -> dict[str, Any]:
    """Start export for a book."""
    try:
        return await _get_service().export(book_id, format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/books/{book_id}/export/download/{filename}")
async def download_export(book_id: str, filename: str) -> FileResponse:
    """Download exported ebook file."""
    service = _get_service()
    try:
        status = service.get_export_status(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Find matching file
    for fmt, path in status["formats"].items():
        if Path(path).name == filename:
            return FileResponse(path, filename=filename)

    raise HTTPException(status_code=404, detail="File not found")
