"""Style API routes — CRUD for translation styles."""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

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


# --- Generate (must be before /{name} to avoid path conflicts) ---


class GenerateRequest(BaseModel):
    description: str


@router.post("/generate")
async def generate_style(body: GenerateRequest) -> dict[str, Any]:
    """Generate a style using LLM."""
    try:
        return await _get_service().generate_style(body.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Import (must be before /{name} to avoid path conflicts) ---


class ImportRequest(BaseModel):
    yaml_content: str


@router.post("/import")
async def import_style(body: ImportRequest) -> dict[str, Any]:
    """Import a style from YAML content."""
    try:
        return _get_service().import_style(body.yaml_content)
    except ValueError as e:
        detail = str(e)
        code = 409 if "already exists" in detail else 422
        raise HTTPException(status_code=code, detail=detail)


# --- Read (existing) ---


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


# --- Create ---


@router.post("", status_code=201)
async def create_style(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new custom style."""
    try:
        return _get_service().create_style(data)
    except ValueError as e:
        detail = str(e)
        code = 409 if "already exists" in detail else 422
        raise HTTPException(status_code=code, detail=detail)


# --- Update ---


@router.put("/{name}")
async def update_style(name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Update an existing custom style."""
    try:
        return _get_service().update_style(name, data)
    except ValueError as e:
        detail = str(e)
        code = 403 if "built-in" in detail.lower() else 404
        raise HTTPException(status_code=code, detail=detail)


# --- Delete ---


@router.delete("/{name}")
async def delete_style(name: str) -> dict[str, str]:
    """Delete a custom style."""
    try:
        _get_service().delete_style(name)
        return {"status": "deleted"}
    except ValueError as e:
        detail = str(e)
        code = 403 if "built-in" in detail.lower() else 404
        raise HTTPException(status_code=code, detail=detail)


# --- Duplicate ---


class DuplicateRequest(BaseModel):
    new_name: str | None = None


@router.post("/{name}/duplicate", status_code=201)
async def duplicate_style(name: str, body: DuplicateRequest | None = None) -> dict[str, Any]:
    """Duplicate a style (shadow or copy)."""
    try:
        new_name = body.new_name if body else None
        return _get_service().duplicate_style(name, new_name=new_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Export ---


@router.get("/{name}/export")
async def export_style(name: str) -> Response:
    """Export a style as YAML file."""
    try:
        yaml_content = _get_service().export_style(name)
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={"Content-Disposition": f'attachment; filename="{name}.yaml"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
