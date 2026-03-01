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

## Task 5: Frontend — Style Editor Form Component

> **UI/UX reference:** Use `@[/ui-ux-pro-max]` — Section 5 of design doc for accessibility, Lucide icons, dynamic lists, save button states, keyboard shortcuts.

**Files:**
- Create: `web/src/components/styles/StyleEditorForm.tsx` (NEW)

**Step 1: Create the form component**

This is the core editing form used in CREATE, EDIT, and SHADOW-EDIT panel modes. It handles:
- All style fields with proper `<label>` elements
- Dynamic add/remove for guidelines, vocabulary, and examples
- Inline validation (on blur)
- Save button states (disabled/ready/saving)
- "Generate with AI" collapsible section
- Keyboard shortcut `Ctrl+S`

The component receives:
- `initialData: StyleDetail | null` — null for CREATE mode, pre-filled for EDIT/SHADOW
- `mode: "create" | "edit" | "shadow-edit"`
- `onSave: (data: StyleDetail) => Promise<void>`
- `onCancel: () => void`
- `onDirtyChange: (dirty: boolean) => void`

Key implementation notes referencing design doc Section 5:
- Use Lucide `Plus`, `Trash2`, `Sparkles` icons (§5.1)
- All inputs have visible `<label htmlFor>` (§5.2)
- Validation errors below each field with `aria-describedby` (§5.2, §5.8)
- Dynamic list rows: `animate-fade-in` on add, each with `Trash2` remove icon (§5.4)
- Tone field: `<select>` dropdown with options `formal|casual|archaic|poetic|literary` (§4)
- Name field: editable only in CREATE mode (§2)
- Save button: 3-state (disabled/ready/saving) per §5.5
- `Ctrl+S` / `Cmd+S` shortcut to save (§5.7)

**Step 2: Commit**

```bash
git add web/src/components/styles/StyleEditorForm.tsx
git commit -m "feat(web): add StyleEditorForm component"
```

---

## Task 6: Frontend — Rewrite Styles Page with Panel Modes

> **UI/UX reference:** Use `@[/ui-ux-pro-max]` design doc Section 2 for panel modes, Section 5 for Lucide icons, focus trap, keyboard shortcuts.

**Files:**
- Modify: `web/src/app/styles/page.tsx`

**Step 1: Refactor the page**

Rewrite `page.tsx` to support 4 panel modes (VIEW, CREATE, SHADOW-EDIT, EDIT):

Key changes:
- **State:** Add `panelMode: "view" | "create" | "edit" | "shadow-edit" | null` state
- **Top action buttons:** "New Style" (`Plus` icon) + "Import YAML" (`Upload` icon) — use Lucide, not emoji
- **Card badges:** Show `style_type` badge with color coding per §2
- **Built-in card action:** "Customize" (`Wrench` icon) button on built-in cards
- **VIEW mode panel header:** Conditional action buttons per style type (§2)
- **EDIT modes:** Render `StyleEditorForm` inside the panel
- **SHADOW-EDIT banner:** Info banner with `PenLine` icon (§2)
- **Focus trap:** When panel opens, trap focus within. `Escape` key closes or guards.
- **Unsaved changes guard:** Track dirty state, show confirmation dialog on backdrop/X click
- **Panel width:** `max-w-xl` in edit modes, `max-w-lg` in view mode (§5.6)
- **Panel exit animation:** Add `slideOutRight` keyframe (§5.9)
- **After save/delete:** Toast via `useToast()`, re-fetch style list
- **Import flow:** File input (hidden), reads YAML, calls `importStyle()`, opens panel in CREATE mode pre-filled
- **Export:** Direct download link via `getStyleExportUrl()`

**Step 2: Run the dev server and verify visually**

```bash
cd web && npm run dev
```

Open `http://localhost:3000/styles` and verify:
- Card grid renders with badges (built-in/custom/customized)
- "New Style" button opens empty form panel
- "Customize" on built-in opens shadow-edit panel
- Edit/Delete/Export buttons appear correctly per style type
- Form validation works (try submitting with empty name)
- Save/Cancel/Escape work correctly
- Toast notifications appear

**Step 3: Commit**

```bash
git add web/src/app/styles/page.tsx
git commit -m "feat(web): full Style Manager with CRUD, shadow, import/export"
```

---

## Task 7: Verification — Run Full Test Suite

**Step 1: Run all Python tests**

```bash
uv run pytest tests/test_style_manager.py tests/test_style_service.py tests/test_style_api.py tests/test_services.py -v
```

Expected: All PASS, including the 3 pre-existing style tests in `test_services.py`.

**Step 2: Lint and format**

```bash
uv run ruff check .
uv run ruff format .
```

**Step 3: Run the full app and verify end-to-end**

```bash
uv run dich-truyen ui
```

1. Open `http://localhost:3000/styles`
2. **Test CREATE:** Click "New Style" → fill form → Save → verify card appears
3. **Test EDIT:** Click the new card → Edit → change description → Save → verify updated
4. **Test DELETE:** Click the card → Delete → confirm → verify card removed
5. **Test CUSTOMIZE:** Click a built-in card → Customize → change a guideline → Save → verify badge changes to "customized"
6. **Test RESET:** Click the customized card → Reset to Default → confirm → verify badge reverts to "built-in"
7. **Test IMPORT:** Click "Import YAML" → select a `.yaml` file → verify form pre-fills → Save
8. **Test EXPORT:** Click any card → Export YAML → verify file downloads

**Step 4: Final commit**

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
| 4 | Frontend API + Types | (type-checked by TypeScript) |
| 5 | `StyleEditorForm` component | (visual verification) |
| 6 | Styles page rewrite | (visual verification) |
| 7 | Full verification | All tests + end-to-end |
