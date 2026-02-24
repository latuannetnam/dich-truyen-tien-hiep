"""Settings API routes — read and update configuration."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

_config_service = None


def set_config_service(service) -> None:
    """Set the ConfigService instance."""
    global _config_service
    _config_service = service


@router.get("")
async def get_settings() -> dict[str, Any]:
    """Get current application settings."""
    return _config_service.get_settings()


@router.put("")
async def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Update application settings."""
    return _config_service.update_settings(updates)


@router.post("/test-connection")
async def test_connection() -> dict[str, Any]:
    """Test LLM API connection."""
    return _config_service.test_connection()
