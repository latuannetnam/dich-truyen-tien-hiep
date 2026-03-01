# Full Style Manager Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add full CRUD, LLM generation, shadow/customize built-ins, and YAML import/export to the Style Manager Web UI.

**Architecture:** Backend-first (core → service → API routes → frontend). Each layer is testable independently. The frontend reuses the existing slide-in panel pattern and extends it with edit/create modes.

**Tech Stack:** Python 3.11+ / FastAPI / Pydantic (backend), Next.js / React / TypeScript / Lucide icons (frontend)

**Design doc:** [2026-03-01-style-manager-design.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/docs/plans/2026-03-01-style-manager-design.md)

---

## Task 1: Core Layer — `StyleManager` CRUD Methods

**Files:**
- Modify: `src/dich_truyen/translator/style.py:244-314`
- Test: `tests/test_style_manager.py` (NEW)

**Step 1: Write the failing tests**

```python
# tests/test_style_manager.py
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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_style_manager.py -v
```

Expected: FAIL — `save`, `delete`, `invalidate_cache`, `is_builtin`, `is_shadow` not defined.

**Step 3: Implement the methods**

Add to `StyleManager` class in `src/dich_truyen/translator/style.py`:

```python
def save(self, template: StyleTemplate) -> None:
    """Save a style template to the custom styles directory.

    Args:
        template: StyleTemplate to save.
    """
    self.styles_dir.mkdir(parents=True, exist_ok=True)
    path = self.styles_dir / f"{template.name}.yaml"
    template.to_yaml(path)
    self.invalidate_cache(template.name)

def delete(self, name: str) -> None:
    """Delete a custom style template.

    Args:
        name: Style name to delete.

    Raises:
        ValueError: If style is built-in or not found.
    """
    if name in BUILT_IN_STYLES and not self._has_custom_file(name):
        raise ValueError(f"Cannot delete built-in style: {name}")
    path = self.styles_dir / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"Custom style file not found: {name}")
    path.unlink()
    self.invalidate_cache(name)
    logger.info("style_deleted", name=name)

def invalidate_cache(self, name: str) -> None:
    """Remove a style from the internal cache.

    Args:
        name: Style name to invalidate.
    """
    self._cache.pop(name, None)

def is_builtin(self, name: str) -> bool:
    """Check if a style name is a built-in style.

    Args:
        name: Style name.

    Returns:
        True if built-in.
    """
    return name in BUILT_IN_STYLES

def is_shadow(self, name: str) -> bool:
    """Check if a custom style shadows a built-in.

    Args:
        name: Style name.

    Returns:
        True if both built-in and custom file exist.
    """
    return name in BUILT_IN_STYLES and self._has_custom_file(name)

def _has_custom_file(self, name: str) -> bool:
    """Check if a custom YAML file exists for this name."""
    return (self.styles_dir / f"{name}.yaml").exists()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_style_manager.py -v
```

Expected: All PASS.

**Step 5: Commit**

```bash
git add src/dich_truyen/translator/style.py tests/test_style_manager.py
git commit -m "feat(style): add CRUD methods to StyleManager"
```

---

## Task 2: Service Layer — `StyleService` CRUD Methods

**Files:**
- Modify: `src/dich_truyen/services/style_service.py`
- Test: `tests/test_style_service.py` (NEW)

**Step 1: Write the failing tests**

```python
# tests/test_style_service.py
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
    """Import valid YAML creates a style."""
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
    assert (styles_dir / "imported_style.yaml").exists()


def test_import_style_invalid_yaml(svc: StyleService) -> None:
    """Import invalid YAML raises ValueError."""
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        svc.import_style("not: valid: yaml: {{{")


def test_import_style_name_collision(svc: StyleService) -> None:
    """Import with existing name raises ValueError."""
    svc.create_style(VALID_STYLE)
    yaml_content = f"""
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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_style_service.py -v
```

Expected: FAIL — methods not defined.

**Step 3: Implement the service methods**

Add to `StyleService` in `src/dich_truyen/services/style_service.py`:

```python
def create_style(self, data: dict[str, Any]) -> dict[str, Any]:
    """Create a new custom style.

    Args:
        data: Style template data.

    Returns:
        Created style as dict.

    Raises:
        ValueError: If name already exists.
    """
    template = StyleTemplate.model_validate(data)
    if template.name in self._manager.list_available():
        raise ValueError(f"Style '{template.name}' already exists")
    self._manager.save(template)
    return self.get_style(template.name)

def update_style(self, name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Update an existing custom style.

    Args:
        name: Style name.
        data: Updated style data.

    Returns:
        Updated style as dict.

    Raises:
        ValueError: If style is a pure built-in (no shadow).
    """
    if self._manager.is_builtin(name) and not self._manager.is_shadow(name):
        raise ValueError(f"Cannot update built-in style: {name}")
    template = StyleTemplate.model_validate(data)
    template.name = name  # Keep original name
    self._manager.save(template)
    return self.get_style(name)

def delete_style(self, name: str) -> None:
    """Delete a custom style.

    Args:
        name: Style name.

    Raises:
        ValueError: If style is built-in or not found.
    """
    self._manager.delete(name)

def duplicate_style(
    self, name: str, new_name: str | None = None
) -> dict[str, Any]:
    """Duplicate a style.

    Args:
        name: Source style name.
        new_name: New name (None keeps same name for shadowing).

    Returns:
        Duplicated style as dict.
    """
    source = self._manager.load(name)
    clone = source.model_copy()
    if new_name:
        clone.name = new_name
    self._manager.save(clone)
    return self.get_style(clone.name)

async def generate_style(self, description: str) -> dict[str, Any]:
    """Generate a style using LLM.

    Args:
        description: Style description in Vietnamese.

    Returns:
        Generated style as dict (not saved).
    """
    from dich_truyen.translator.style import generate_style_from_description

    template = await generate_style_from_description(description)
    return {
        "name": template.name,
        "description": template.description,
        "guidelines": template.guidelines,
        "vocabulary": template.vocabulary,
        "tone": template.tone,
        "examples": [
            {"chinese": ex.get("chinese", ""), "vietnamese": ex.get("vietnamese", "")}
            if isinstance(ex, dict)
            else {"chinese": ex.chinese, "vietnamese": ex.vietnamese}
            for ex in (template.examples or [])
        ],
    }

def import_style(self, yaml_content: str) -> dict[str, Any]:
    """Import a style from YAML string.

    Args:
        yaml_content: YAML content string.

    Returns:
        Imported style as dict.

    Raises:
        ValueError: If YAML is invalid or name collision.
    """
    import yaml

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        raise ValueError("Invalid YAML: expected a mapping")

    try:
        template = StyleTemplate.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid style template: {e}")

    if template.name in self._manager.list_available():
        raise ValueError(f"Style '{template.name}' already exists")

    self._manager.save(template)
    return self.get_style(template.name)

def export_style(self, name: str) -> str:
    """Export a style as YAML string.

    Args:
        name: Style name.

    Returns:
        YAML string.

    Raises:
        ValueError: If style not found.
    """
    import yaml

    template = self._manager.load(name)
    return yaml.dump(
        template.model_dump(),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )

def get_style_type(self, name: str) -> str:
    """Get the type of a style: 'builtin', 'custom', or 'shadow'.

    Args:
        name: Style name.

    Returns:
        Style type string.
    """
    if self._manager.is_shadow(name):
        return "shadow"
    if self._manager.is_builtin(name):
        return "builtin"
    return "custom"
```

Also update `list_styles()` to include `style_type`:

```python
# In list_styles(), change the append to include style_type:
styles.append({
    "name": template.name,
    "description": template.description,
    "tone": template.tone,
    "is_builtin": name in built_in,
    "style_type": self.get_style_type(name),
})
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_style_service.py -v
```

Expected: All PASS.

**Step 5: Commit**

```bash
git add src/dich_truyen/services/style_service.py tests/test_style_service.py
git commit -m "feat(style): add CRUD methods to StyleService"
```

---

## Task 3: API Routes — CRUD Endpoints

**Files:**
- Modify: `src/dich_truyen/api/routes/styles.py`
- Test: `tests/test_style_api.py` (NEW)

**Step 1: Write the failing tests**

```python
# tests/test_style_api.py
"""Tests for Style API CRUD routes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dich_truyen.api.routes import styles
from dich_truyen.services.style_service import StyleService


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a test client with style routes."""
    from fastapi import FastAPI

    app = FastAPI()
    styles_dir = tmp_path / "styles"
    styles_dir.mkdir()
    svc = StyleService(styles_dir=styles_dir)
    styles.set_style_service(svc)
    app.include_router(styles.router)
    return TestClient(app)


VALID_STYLE = {
    "name": "test_api",
    "description": "API test style",
    "guidelines": ["Rule 1"],
    "vocabulary": {"你": "ngươi"},
    "tone": "formal",
    "examples": [{"chinese": "你好", "vietnamese": "Xin chào"}],
}


def test_create_style(client: TestClient) -> None:
    """POST /api/v1/styles creates a style."""
    r = client.post("/api/v1/styles", json=VALID_STYLE)
    assert r.status_code == 201
    assert r.json()["name"] == "test_api"


def test_create_style_duplicate(client: TestClient) -> None:
    """POST /api/v1/styles with existing name returns 409."""
    client.post("/api/v1/styles", json=VALID_STYLE)
    r = client.post("/api/v1/styles", json=VALID_STYLE)
    assert r.status_code == 409


def test_update_style(client: TestClient) -> None:
    """PUT /api/v1/styles/{name} updates a style."""
    client.post("/api/v1/styles", json=VALID_STYLE)
    r = client.put(
        "/api/v1/styles/test_api",
        json={**VALID_STYLE, "description": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Updated"


def test_update_builtin_rejected(client: TestClient) -> None:
    """PUT /api/v1/styles/{name} for built-in returns 403."""
    r = client.put("/api/v1/styles/tien_hiep", json=VALID_STYLE)
    assert r.status_code == 403


def test_delete_style(client: TestClient) -> None:
    """DELETE /api/v1/styles/{name} removes a style."""
    client.post("/api/v1/styles", json=VALID_STYLE)
    r = client.delete("/api/v1/styles/test_api")
    assert r.status_code == 200


def test_delete_builtin_rejected(client: TestClient) -> None:
    """DELETE /api/v1/styles/{name} for built-in returns 403."""
    r = client.delete("/api/v1/styles/tien_hiep")
    assert r.status_code == 403


def test_duplicate_style(client: TestClient) -> None:
    """POST /api/v1/styles/{name}/duplicate clones a style."""
    r = client.post("/api/v1/styles/tien_hiep/duplicate")
    assert r.status_code == 201
    assert r.json()["name"] == "tien_hiep"


def test_import_style(client: TestClient) -> None:
    """POST /api/v1/styles/import accepts YAML."""
    yaml_content = """
name: imported
description: From YAML
guidelines:
  - Rule
tone: formal
"""
    r = client.post("/api/v1/styles/import", json={"yaml_content": yaml_content})
    assert r.status_code == 201
    assert r.json()["name"] == "imported"


def test_import_invalid_yaml(client: TestClient) -> None:
    """POST /api/v1/styles/import with bad YAML returns 422."""
    r = client.post("/api/v1/styles/import", json={"yaml_content": "{{{bad"})
    assert r.status_code == 422


def test_export_style(client: TestClient) -> None:
    """GET /api/v1/styles/{name}/export returns YAML."""
    r = client.get("/api/v1/styles/tien_hiep/export")
    assert r.status_code == 200
    assert "tien_hiep" in r.text
    assert r.headers["content-type"].startswith("application/x-yaml")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_style_api.py -v
```

Expected: FAIL — routes not defined.

**Step 3: Implement the API routes**

Rewrite `src/dich_truyen/api/routes/styles.py`:

```python
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
async def duplicate_style(
    name: str, body: DuplicateRequest | None = None
) -> dict[str, Any]:
    """Duplicate a style (shadow or copy)."""
    try:
        new_name = body.new_name if body else None
        return _get_service().duplicate_style(name, new_name=new_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Generate ---

class GenerateRequest(BaseModel):
    description: str


@router.post("/generate")
async def generate_style(body: GenerateRequest) -> dict[str, Any]:
    """Generate a style using LLM."""
    try:
        return await _get_service().generate_style(body.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Import ---

class ImportRequest(BaseModel):
    yaml_content: str


@router.post("/import", status_code=201)
async def import_style(body: ImportRequest) -> dict[str, Any]:
    """Import a style from YAML content."""
    try:
        return _get_service().import_style(body.yaml_content)
    except ValueError as e:
        detail = str(e)
        code = 409 if "already exists" in detail else 422
        raise HTTPException(status_code=code, detail=detail)


# --- Export ---

@router.get("/{name}/export")
async def export_style(name: str) -> Response:
    """Export a style as YAML file."""
    try:
        yaml_content = _get_service().export_style(name)
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f'attachment; filename="{name}.yaml"'
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

> **IMPORTANT:** The `/generate` and `/import` routes must be registered BEFORE `/{name}` to avoid path conflicts. Move them above the `/{name}` GET route, or use more specific path patterns.

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_style_api.py -v
```

Expected: All PASS.

**Step 5: Also run existing tests to verify no regressions**

```bash
uv run pytest tests/test_services.py -v
```

Expected: All PASS (existing `test_style_service_*` tests still work).

**Step 6: Commit**

```bash
git add src/dich_truyen/api/routes/styles.py tests/test_style_api.py
git commit -m "feat(api): add CRUD routes for styles"
```

---

## Task 4: Frontend — API Client & Types

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/lib/api.ts`

**Step 1: Update TypeScript types**

In `web/src/lib/types.ts`, update `StyleSummary` to include `style_type` and add request types:

```typescript
/** Style template summary. */
export interface StyleSummary {
  name: string;
  description: string;
  tone: string;
  is_builtin: boolean;
  style_type: "builtin" | "custom" | "shadow";
}

/** Full style template (also used as create/update payload). */
export interface StyleDetail {
  name: string;
  description: string;
  guidelines: string[];
  vocabulary: Record<string, string>;
  tone: string;
  examples: { chinese: string; vietnamese: string }[];
}
```

**Step 2: Add API functions**

In `web/src/lib/api.ts`, add after the existing `getStyle` function:

```typescript
export async function createStyle(data: StyleDetail): Promise<StyleDetail> {
  const res = await fetch(`${API_BASE}/styles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function updateStyle(
  name: string,
  data: StyleDetail
): Promise<StyleDetail> {
  const res = await fetch(`${API_BASE}/styles/${name}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function deleteStyle(name: string): Promise<void> {
  const res = await fetch(`${API_BASE}/styles/${name}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
}

export async function duplicateStyle(
  name: string,
  newName?: string
): Promise<StyleDetail> {
  const res = await fetch(`${API_BASE}/styles/${name}/duplicate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_name: newName ?? null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function generateStyle(
  description: string
): Promise<StyleDetail> {
  const res = await fetch(`${API_BASE}/styles/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function importStyle(yamlContent: string): Promise<StyleDetail> {
  const res = await fetch(`${API_BASE}/styles/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export function getStyleExportUrl(name: string): string {
  return `${API_BASE}/styles/${name}/export`;
}
```

**Step 3: Commit**

```bash
git add web/src/lib/types.ts web/src/lib/api.ts
git commit -m "feat(web): add style CRUD API client functions"
```

---

## Task 5: Frontend — Shared UI Components

> **UI/UX source:** ui-ux-pro-max — web-interface (focus, forms, destructive actions), ux-guidelines (animation, reduced motion)

**Files:**
- Create: `web/src/components/styles/ConfirmDialog.tsx` (NEW)
- Create: `web/src/hooks/useFocusTrap.ts` (NEW)

**Step 1: Create `ConfirmDialog` component**

Used for delete and reset-to-default confirmations. Must be a proper accessible dialog:

```tsx
// web/src/components/styles/ConfirmDialog.tsx
"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  confirmVariant?: "danger" | "default";
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open, title, message, confirmLabel,
  confirmVariant = "danger", onConfirm, onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onCancel]);

  if (!open) return null;

  const confirmClass = confirmVariant === "danger"
    ? "bg-red-600 hover:bg-red-700 text-white"
    : "bg-blue-600 hover:bg-blue-700 text-white";

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
    >
      <div
        className="bg-[#1E293B] border border-white/10 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-3">
          <AlertTriangle size={20} className="text-amber-400 shrink-0" aria-hidden="true" />
          <h3 id="confirm-title" className="text-lg font-semibold text-white">{title}</h3>
        </div>
        <p className="text-sm text-gray-300 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded-lg bg-white/10 hover:bg-white/20
                       text-gray-300 transition-colors cursor-pointer
                       focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm rounded-lg transition-colors cursor-pointer
                        focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none
                        ${confirmClass}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
```

Key UX rules applied:
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (accessibility)
- Focus moves to Cancel button on open (safe default per destructive action UX)
- `Escape` key closes dialog
- Click-outside-to-cancel via backdrop `onClick`
- `focus-visible:ring-2` on all buttons (web-interface Critical: never remove outline without replacement)
- `cursor-pointer` on all interactive elements
- Transition on hover (150-300ms range)

**Step 2: Create `useFocusTrap` hook**

```typescript
// web/src/hooks/useFocusTrap.ts
import { useEffect, useRef } from "react";

export function useFocusTrap(active: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !containerRef.current) return;

    const container = containerRef.current;
    const focusable = container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input:not([disabled]), select, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    // Focus first element on open
    first?.focus();

    const handler = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };

    container.addEventListener("keydown", handler);
    return () => container.removeEventListener("keydown", handler);
  }, [active]);

  return containerRef;
}
```

Key UX rules applied:
- Tab cycles within panel only (keyboard navigation: tab order matches visual order)
- Shift+Tab wraps backwards
- Auto-focuses first focusable element on open

**Step 3: Commit**

```bash
git add web/src/components/styles/ConfirmDialog.tsx web/src/hooks/useFocusTrap.ts
git commit -m "feat(web): add ConfirmDialog and useFocusTrap for Style Manager"
```

---

## Task 6: Frontend — Style Editor Form Component

> **UI/UX source:** ui-ux-pro-max — design doc §5 (all 10 subsections)

**Files:**
- Create: `web/src/components/styles/StyleEditorForm.tsx` (NEW)

**Step 1: Create the form component**

Component props:
```typescript
interface StyleEditorFormProps {
  initialData: StyleDetail | null;     // null = CREATE mode (empty)
  mode: "create" | "edit" | "shadow-edit";
  onSave: (data: StyleDetail) => Promise<void>;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
}
```

**Form layout (top to bottom):**

| Section | Fields | Notes |
|---------|--------|-------|
| Header | Mode-specific banner | SHADOW-EDIT shows `PenLine` + "Customizing built-in style" |
| Name | `<input>` | Editable only in CREATE; locked in EDIT/SHADOW |
| Description | `<textarea rows={2}>` | Required, 5-200 chars |
| Tone | `<select>` dropdown | Options: formal, casual, archaic, poetic, literary |
| Guidelines | Dynamic list of `<input>` rows | At least 1 entry; `Plus`/`Trash2` icons |
| Vocabulary | Dynamic key-value rows (two `<input>` per row) | Optional; responsive layout |
| Examples | Dynamic pairs of `<textarea>` (Chinese + Vietnamese) | Optional; `Plus`/`Trash2` |
| AI Generate | Collapsible section | `Sparkles` icon; only in CREATE mode |
| Actions | Save / Cancel buttons | 3-state save button |

**Critical UX implementation details (from ui-ux-pro-max searches):**

1. **Every `<input>` / `<textarea>` / `<select>` MUST have a visible `<label>` with `htmlFor`** (web-interface Critical). No placeholder-only inputs.

2. **Inline validation errors placed BELOW the field:**
   ```tsx
   <label htmlFor="style-name" className="...">Name</label>
   <input id="style-name" aria-describedby={errors.name ? "name-error" : undefined} ... />
   {errors.name && (
     <span id="name-error" className="text-red-400 text-xs mt-1" role="alert">
       {errors.name}
     </span>
   )}
   ```
   Uses `aria-describedby` + `role="alert"` (not just red color — color alone violates accessibility).

3. **On submit with errors: auto-focus the first invalid field.** This is a High severity UX rule for inline errors.

4. **Dynamic list add/remove (Guidelines, Vocabulary, Examples):**
   - `[+ Add]` button with `Plus` icon at bottom of each list
   - `Trash2` icon button to remove, with `aria-label="Remove guideline 3"`
   - Last guideline cannot be removed (disable `Trash2`, show tooltip "At least one guideline required")
   - New rows appear with `animate-fade-in` (ease-out, 200ms)
   - Respect `prefers-reduced-motion`: disable animation if user prefers

5. **Vocabulary table responsive handling:**
   - Desktop: two columns side by side (Chinese + Vietnamese)
   - Below 640px: stack vertically (full-width inputs)

6. **Save button 3-state implementation:**
   ```tsx
   <button
     disabled={!isDirty || hasErrors || isSaving}
     className={`... cursor-pointer
       ${(!isDirty || hasErrors) ? "opacity-50 cursor-not-allowed" : ""}
       focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none`}
   >
     {isSaving ? (
       <><Loader2 size={16} className="animate-spin" /> Saving...</>
     ) : (
       mode === "shadow-edit" ? "Save Customization" : "Save"
     )}
   </button>
   ```

7. **`Ctrl+S` / `Cmd+S` keyboard shortcut:**
   ```tsx
   useEffect(() => {
     const handler = (e: KeyboardEvent) => {
       if ((e.ctrlKey || e.metaKey) && e.key === "s") {
         e.preventDefault();
         if (isDirty && !hasErrors && !isSaving) handleSave();
       }
     };
     window.addEventListener("keydown", handler);
     return () => window.removeEventListener("keydown", handler);
   }, [isDirty, hasErrors, isSaving]);
   ```

8. **AI Generate section (CREATE mode only):**
   - Hidden by default, revealed by clicking `Sparkles` "Generate with AI" button
   - Contains: description `<textarea>` + `[Generate]` button
   - Generate button shows `Loader2` spinner while API call runs (~3-5s)
   - On success: fills all form fields from response, marks form dirty
   - On failure: inline error below textarea with retry guidance

9. **`focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none` on ALL interactive elements** (web-interface Critical: never remove outline without replacement).

10. **`prefers-reduced-motion` respected:**
    ```css
    @media (prefers-reduced-motion: reduce) {
      .animate-fade-in { animation: none; }
    }
    ```

**Step 2: Commit**

```bash
git add web/src/components/styles/StyleEditorForm.tsx
git commit -m "feat(web): add StyleEditorForm component"
```

---

## Task 7: Frontend — Rewrite Styles Page with Panel Modes

> **UI/UX source:** ui-ux-pro-max — design doc §2 (panel modes), §5 (icons, focus, keyboard)

**Files:**
- Modify: `web/src/app/styles/page.tsx`

**Step 1: Refactor the page**

Rewrite `page.tsx` to support all 4 panel modes. The page structure:

```
┌───────────────────────────────────────────────────┐
│  Styles Manager                  [+ New] [Import] │
├───────────────────────────────────────────────────┤
│  [Search...]                                      │
├───────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐             │
│  │ Card    │ │ Card    │ │ Card    │             │
│  │ [badge] │ │ [badge] │ │ [badge] │             │
│  │         │ │ [Cust.] │ │         │             │
│  └─────────┘ └─────────┘ └─────────┘             │
│              ┌──────────────────────┐             │
│              │  Slide-in Panel      │             │
│              │  (VIEW/EDIT/CREATE)  │             │
│              │                      │             │
│              └──────────────────────┘             │
└───────────────────────────────────────────────────┘
```

**Key implementation details:**

1. **State management:**
   ```tsx
   const [panelMode, setPanelMode] = useState<"view" | "create" | "edit" | "shadow-edit" | null>(null);
   const [selectedStyle, setSelectedStyle] = useState<StyleDetail | null>(null);
   const [isDirty, setIsDirty] = useState(false);
   const [isClosing, setIsClosing] = useState(false); // for exit animation
   ```

2. **Top action bar (Lucide icons, NO emojis):**
   ```tsx
   <button aria-label="Create new style"> <Plus size={18} /> New Style </button>
   <button aria-label="Import YAML file"> <Upload size={18} /> Import YAML </button>
   ```
   Both buttons: `cursor-pointer`, `focus-visible:ring-2`, hover color transition 200ms.

3. **Card badges per `style_type`:**
   ```tsx
   const badgeConfig = {
     builtin:  { label: "built-in",    className: "bg-blue-500/20 text-blue-300" },
     custom:   { label: "custom",      className: "bg-green-500/20 text-green-300" },
     shadow:   { label: "customized",  className: "bg-amber-500/20 text-amber-300" },
   };
   ```
   Each badge has `aria-label={`Style type: ${badge.label}`}` (screen reader context).

4. **"Customize" button on built-in cards:**
   ```tsx
   {style.style_type === "builtin" && (
     <button
       onClick={(e) => { e.stopPropagation(); handleCustomize(style.name); }}
       aria-label={`Customize ${style.name}`}
       className="... cursor-pointer focus-visible:ring-2 ..."
     >
       <Wrench size={14} /> Customize
     </button>
   )}
   ```
   `e.stopPropagation()` prevents the card click (which opens VIEW mode).

5. **VIEW mode panel header — conditional actions per style type:**
   | Built-in | `[Customize]` `[Export]` |
   | Custom | `[Edit]` `[Delete]` `[Export]` |
   | Shadow | `[Edit]` `[Reset to Default]` `[Export]` |

   All action buttons: icon + text, `aria-label`, `cursor-pointer`, `focus-visible:ring-2`.

6. **Focus trap via `useFocusTrap` hook (from Task 5):**
   ```tsx
   const panelRef = useFocusTrap(panelMode !== null);
   <div ref={panelRef} role="dialog" aria-modal="true" aria-labelledby="panel-title"> ... </div>
   ```

7. **Escape key handling with dirty guard:**
   ```tsx
   useEffect(() => {
     const handler = (e: KeyboardEvent) => {
       if (e.key === "Escape" && panelMode) {
         if (isDirty) {
           setShowDiscardDialog(true); // "Discard unsaved changes?"
         } else {
           closePanel();
         }
       }
     };
     window.addEventListener("keydown", handler);
     return () => window.removeEventListener("keydown", handler);
   }, [panelMode, isDirty]);
   ```

8. **Panel close animation (§5.9):**
   Add `slideOutRight` keyframe to the page or `globals.css`:
   ```css
   @keyframes slideOutRight {
     from { transform: translateX(0); opacity: 1; }
     to   { transform: translateX(100%); opacity: 0; }
   }
   ```
   On close: set `isClosing=true`, apply `animation: slideOutRight 200ms ease-in`, then `setPanelMode(null)` after animation ends.
   Respect `prefers-reduced-motion: reduce` — skip animation, close instantly.

9. **Panel width toggle (§5.6):**
   ```tsx
   className={panelMode === "view" ? "max-w-lg" : "max-w-xl"}
   ```

10. **Import flow:**
    ```tsx
    <input type="file" accept=".yaml,.yml" ref={fileInputRef} className="hidden" onChange={handleImport} />
    ```
    `handleImport`: reads file as text → calls `importStyle()` to validate → on success opens panel in CREATE mode pre-filled → on error shows toast with specific error.

11. **Export:** Direct `<a>` download link:
    ```tsx
    <a href={getStyleExportUrl(style.name)} download={`${style.name}.yaml`} ...>
      <Download size={16} /> Export YAML
    </a>
    ```

12. **Delete / Reset confirmation — uses `ConfirmDialog` from Task 5:**
    - Delete: title "Delete Style", message `Delete '${name}'? This cannot be undone.`, confirmLabel "Delete", variant `danger`
    - Reset: title "Reset to Default", message `Reset '${name}' to default? Your customizations will be removed.`, confirmLabel "Reset", variant `danger`

13. **After save/delete operations:**
    - Call `useToast().showSuccess("Style saved")` or `showSuccess("Style deleted")`
    - Re-fetch `getStyles()` to refresh card grid
    - Switch panel to VIEW mode (after save) or close panel (after delete)

**Step 2: Commit**

```bash
git add web/src/app/styles/page.tsx
git commit -m "feat(web): full Style Manager with CRUD, shadow, import/export"
```

---

## Task 8: Verification — Full Test Suite + Browser Testing

**Step 1: Run all Python tests**

```bash
uv run pytest tests/test_style_manager.py tests/test_style_service.py tests/test_style_api.py tests/test_services.py -v
```

Expected: All PASS, including 3 pre-existing style tests in `test_services.py`.

**Step 2: Lint and format**

```bash
uv run ruff check .
uv run ruff format .
```

**Step 3: TypeScript check**

```bash
cd web && npx tsc --noEmit
```

Expected: No type errors.

**Step 4: Run the full app and verify end-to-end**

Start the app:
```bash
uv run dich-truyen ui
```

Open `http://localhost:3000/styles` and run through this checklist:

**Functional tests:**
1. **CREATE:** Click "New Style" → fill all fields → Save → verify new card appears with green "custom" badge
2. **EDIT:** Click the new card → Edit → change description → Save → verify description updated
3. **DELETE:** Click the card → Delete → confirm dialog appears → confirm → verify card removed + toast
4. **CUSTOMIZE:** Click a built-in card → Customize → change a guideline → Save → verify badge changes to orange "customized"
5. **RESET:** Click the customized card → Reset to Default → confirm → verify badge reverts to blue "built-in"
6. **IMPORT:** Click "Import YAML" → select a `.yaml` file → verify form pre-fills → review → Save
7. **EXPORT:** Click any card → Export YAML → verify `.yaml` file downloads
8. **AI GENERATE:** Click "New Style" → "Generate with AI" → type description → Generate → verify form fills

**UX/Accessibility tests (from ui-ux-pro-max pre-delivery checklist):**

| # | Check | How to verify |
|---|-------|---------------|
| 1 | No emoji icons visible | Visually scan — all icons should be Lucide SVG |
| 2 | All buttons have `cursor-pointer` | Hover over every button — cursor should change |
| 3 | Focus-visible rings on tab | Press Tab repeatedly — each interactive element shows blue ring |
| 4 | Escape closes panel | Open panel → press Escape → panel closes |
| 5 | Escape with dirty form shows dialog | Edit something → press Escape → "Discard changes?" appears |
| 6 | Focus trapped in panel | Open panel → Tab through all elements → focus should NOT leave panel |
| 7 | ConfirmDialog has focus on Cancel | Click Delete → dialog opens → Cancel button is focused |
| 8 | All form inputs have visible labels | Check Name, Description, Tone, Guidelines all have `<label>` text |
| 9 | Validation errors below fields | Leave Name blank → blur → red error text appears below field |
| 10 | Hover transitions are smooth (not instant) | Hover over cards, buttons — should be 200ms color transition |
| 11 | Badge on each card | Every card shows a badge (built-in / custom / customized) |
| 12 | Ctrl+S saves in edit mode | Open edit → change something → Ctrl+S → style saved |
| 13 | Toast appears after save/delete | Save or delete → green toast at bottom-right, auto-dismiss 3s |

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: full Style Manager — CRUD, shadow, LLM generate, import/export"
```

---

## Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | `StyleManager` CRUD (core) | `test_style_manager.py` — 10 tests |
| 2 | `StyleService` CRUD (service) | `test_style_service.py` — 14 tests |
| 3 | API routes (FastAPI) | `test_style_api.py` — 11 tests |
| 4 | Frontend API + Types | TypeScript `tsc --noEmit` |
| 5 | `ConfirmDialog` + `useFocusTrap` | Browser verification |
| 6 | `StyleEditorForm` component | Browser verification |
| 7 | Styles page rewrite | Browser verification |
| 8 | Full verification | 35+ unit tests + 13-point browser checklist |
