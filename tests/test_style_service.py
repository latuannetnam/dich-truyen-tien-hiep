"""Tests for StyleService CRUD operations."""

from pathlib import Path

import pytest

from dich_truyen.services.style_service import StyleService


@pytest.fixture
def styles_dir(tmp_path: Path) -> Path:
    """Create empty custom styles dir."""
    d = tmp_path / "styles"
    d.mkdir()
    return d


@pytest.fixture
def svc(styles_dir: Path) -> StyleService:
    return StyleService(styles_dir=styles_dir)


VALID_STYLE = {
    "name": "my_custom",
    "description": "A custom style",
    "guidelines": ["Rule 1", "Rule 2"],
    "vocabulary": {"你": "ngươi"},
    "tone": "formal",
    "examples": [{"chinese": "你好", "vietnamese": "Xin chào"}],
}


# --- create_style ---


def test_create_style(svc: StyleService, styles_dir: Path) -> None:
    """Create saves file and returns dict."""
    result = svc.create_style(VALID_STYLE)
    assert result["name"] == "my_custom"
    assert (styles_dir / "my_custom.yaml").exists()


def test_create_style_name_collision(svc: StyleService) -> None:
    """Cannot create style with existing name."""
    svc.create_style(VALID_STYLE)
    with pytest.raises(ValueError, match="already exists"):
        svc.create_style(VALID_STYLE)


def test_create_style_builtin_name(svc: StyleService) -> None:
    """Cannot create style with built-in name."""
    data = {**VALID_STYLE, "name": "tien_hiep"}
    with pytest.raises(ValueError, match="already exists"):
        svc.create_style(data)


# --- update_style ---


def test_update_style(svc: StyleService) -> None:
    """Update changes custom style data."""
    svc.create_style(VALID_STYLE)
    updated = svc.update_style("my_custom", {**VALID_STYLE, "description": "Updated"})
    assert updated["description"] == "Updated"


def test_update_builtin_rejected(svc: StyleService) -> None:
    """Cannot update a pure built-in style."""
    with pytest.raises(ValueError, match="[Bb]uilt.in"):
        svc.update_style("tien_hiep", VALID_STYLE)


# --- delete_style ---


def test_delete_style(svc: StyleService, styles_dir: Path) -> None:
    """Delete removes the custom style."""
    svc.create_style(VALID_STYLE)
    svc.delete_style("my_custom")
    assert not (styles_dir / "my_custom.yaml").exists()


def test_delete_builtin_rejected(svc: StyleService) -> None:
    """Cannot delete a built-in style."""
    with pytest.raises(ValueError):
        svc.delete_style("tien_hiep")


# --- duplicate_style ---


def test_duplicate_builtin(svc: StyleService, styles_dir: Path) -> None:
    """Duplicate built-in creates a shadow file."""
    result = svc.duplicate_style("tien_hiep")
    assert result["name"] == "tien_hiep"
    assert (styles_dir / "tien_hiep.yaml").exists()


def test_duplicate_custom_with_new_name(svc: StyleService, styles_dir: Path) -> None:
    """Duplicate custom creates copy with new name."""
    svc.create_style(VALID_STYLE)
    result = svc.duplicate_style("my_custom", new_name="my_custom_copy")
    assert result["name"] == "my_custom_copy"
    assert (styles_dir / "my_custom_copy.yaml").exists()


# --- generate_style ---


@pytest.mark.asyncio
async def test_generate_style(svc: StyleService) -> None:
    """Generate returns a valid style dict (mocked LLM)."""
    # This test uses the fallback path (no LLM configured)
    result = await svc.generate_style("Phong cách tiên hiệp mới")
    assert "name" in result
    assert "guidelines" in result


# --- import_style ---


def test_import_style(svc: StyleService, styles_dir: Path) -> None:
    """Import valid YAML validates and returns parsed style (not saved)."""
    yaml_content = """
name: imported_style
description: Imported from file
guidelines:
  - Rule 1
vocabulary: {}
tone: formal
examples: []
"""
    result = svc.import_style(yaml_content)
    assert result["name"] == "imported_style"
    # import_style validates only; file is NOT created until create_style
    assert not (styles_dir / "imported_style.yaml").exists()


def test_import_style_invalid_yaml(svc: StyleService) -> None:
    """Import invalid YAML raises ValueError."""
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        svc.import_style("not: valid: yaml: {{{")


def test_import_style_name_collision(svc: StyleService) -> None:
    """Import with existing name raises ValueError."""
    svc.create_style(VALID_STYLE)
    yaml_content = """
name: my_custom
description: Collision
guidelines:
  - Rule
tone: formal
"""
    with pytest.raises(ValueError, match="already exists"):
        svc.import_style(yaml_content)


# --- export_style ---


def test_export_style(svc: StyleService) -> None:
    """Export returns YAML string."""
    result = svc.export_style("tien_hiep")
    assert "name:" in result
    assert "tien_hiep" in result


# --- get_style_type ---


def test_get_style_type_builtin(svc: StyleService) -> None:
    """Built-in returns 'builtin'."""
    assert svc.get_style_type("tien_hiep") == "builtin"


def test_get_style_type_custom(svc: StyleService) -> None:
    """Custom returns 'custom'."""
    svc.create_style(VALID_STYLE)
    assert svc.get_style_type("my_custom") == "custom"


def test_get_style_type_shadow(svc: StyleService) -> None:
    """Shadow returns 'shadow'."""
    svc.duplicate_style("tien_hiep")
    assert svc.get_style_type("tien_hiep") == "shadow"
