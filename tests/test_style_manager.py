"""Tests for StyleManager CRUD operations."""

import yaml
from pathlib import Path

import pytest

from dich_truyen.translator.style import StyleManager, StyleTemplate, BUILT_IN_STYLES


@pytest.fixture
def styles_dir(tmp_path: Path) -> Path:
    """Create an empty custom styles directory."""
    d = tmp_path / "styles"
    d.mkdir()
    return d


@pytest.fixture
def manager(styles_dir: Path) -> StyleManager:
    """StyleManager with temp custom dir."""
    return StyleManager(styles_dir=styles_dir)


# --- save ---

def test_save_new_style(manager: StyleManager, styles_dir: Path) -> None:
    """Save creates a YAML file in the custom dir."""
    template = StyleTemplate(
        name="test_style",
        description="Test description",
        guidelines=["Guideline 1"],
        vocabulary={"你": "ngươi"},
        tone="formal",
        examples=[{"chinese": "你好", "vietnamese": "Xin chào"}],
    )
    manager.save(template)

    yaml_path = styles_dir / "test_style.yaml"
    assert yaml_path.exists()
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert data["name"] == "test_style"
    assert data["tone"] == "formal"


def test_save_invalidates_cache(manager: StyleManager, styles_dir: Path) -> None:
    """Save clears cached entry so next load gets fresh data."""
    template = StyleTemplate(name="cached", description="v1", guidelines=["g1"])
    manager.save(template)
    _ = manager.load("cached")  # populate cache
    assert "cached" in manager._cache

    template2 = StyleTemplate(name="cached", description="v2", guidelines=["g2"])
    manager.save(template2)
    assert "cached" not in manager._cache  # cache invalidated

    reloaded = manager.load("cached")
    assert reloaded.description == "v2"


# --- delete ---

def test_delete_custom_style(manager: StyleManager, styles_dir: Path) -> None:
    """Delete removes the YAML file."""
    template = StyleTemplate(name="to_delete", description="bye", guidelines=["g"])
    manager.save(template)
    assert (styles_dir / "to_delete.yaml").exists()

    manager.delete("to_delete")
    assert not (styles_dir / "to_delete.yaml").exists()


def test_delete_invalidates_cache(manager: StyleManager, styles_dir: Path) -> None:
    """Delete clears the cached entry."""
    template = StyleTemplate(name="cached_del", description="d", guidelines=["g"])
    manager.save(template)
    _ = manager.load("cached_del")
    assert "cached_del" in manager._cache

    manager.delete("cached_del")
    assert "cached_del" not in manager._cache


def test_delete_nonexistent_raises(manager: StyleManager) -> None:
    """Delete nonexistent style raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        manager.delete("nonexistent")


def test_delete_builtin_raises(manager: StyleManager) -> None:
    """Cannot delete a built-in style."""
    with pytest.raises(ValueError, match="[Bb]uilt.in"):
        manager.delete("tien_hiep")


# --- invalidate_cache ---

def test_invalidate_cache(manager: StyleManager) -> None:
    """Invalidate removes one entry from cache."""
    _ = manager.load("tien_hiep")
    assert "tien_hiep" in manager._cache
    manager.invalidate_cache("tien_hiep")
    assert "tien_hiep" not in manager._cache


def test_invalidate_cache_missing_key_noop(manager: StyleManager) -> None:
    """Invalidating a non-cached key does nothing."""
    manager.invalidate_cache("not_cached")  # should not raise


# --- is_builtin ---

def test_is_builtin(manager: StyleManager) -> None:
    """Check built-in detection."""
    assert manager.is_builtin("tien_hiep") is True
    assert manager.is_builtin("nonexistent") is False


# --- is_shadow ---

def test_is_shadow(manager: StyleManager, styles_dir: Path) -> None:
    """Custom file with same name as built-in is a shadow."""
    template = StyleTemplate(name="tien_hiep", description="custom", guidelines=["g"])
    manager.save(template)
    assert manager.is_shadow("tien_hiep") is True
    assert manager.is_shadow("kiem_hiep") is False
