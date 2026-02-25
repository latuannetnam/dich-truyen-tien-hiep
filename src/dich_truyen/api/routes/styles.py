"""Style API routes — CRUD for translation styles."""

from typing import Any

from fastapi import APIRouter, HTTPException

from dich_truyen.services.style_service import StyleService

router = APIRouter(prefix="/api/v1/styles", tags=["styles"])

_style_service: StyleService | None = None


def set_style_service(service: StyleService) -> None:
    """Set the style service instance."""
    global _style_service
    _style_service = service


def _get_service() -> StyleService:
    if _style_service is None:
        return StyleService()
    return _style_service


@router.get("")
async def list_styles() -> list[dict[str, Any]]:
    """List all available style templates."""
    return _get_service().list_styles()


@router.get("/{name}")
async def get_style(name: str) -> dict[str, Any]:
    """Get a style template by name."""
    try:
        return _get_service().get_style(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
