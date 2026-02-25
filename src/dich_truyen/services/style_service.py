"""StyleService — business logic for translation style management.

Wraps StyleManager behind a clean interface suitable for REST endpoints
and future CLI refactoring.
"""

from pathlib import Path
from typing import Any, Optional

from dich_truyen.translator.style import StyleManager, StyleTemplate


class StyleService:
    """Manage translation style templates.

    Provides a dict-based API over StyleManager so route handlers
    stay thin and logic can be tested without HTTP.
    """

    def __init__(self, styles_dir: Optional[Path] = None) -> None:
        self._manager = StyleManager(styles_dir=styles_dir)

    def list_styles(self) -> list[dict[str, Any]]:
        """List all available style templates with metadata.

        Returns:
            List of dicts with 'name', 'description', and 'is_builtin'.
        """
        styles: list[dict[str, Any]] = []
        built_in = set(self._manager.get_built_in_names())

        for name in self._manager.list_available():
            try:
                template = self._manager.load(name)
                styles.append({
                    "name": template.name,
                    "description": template.description,
                    "tone": template.tone,
                    "is_builtin": name in built_in,
                })
            except Exception:
                styles.append({
                    "name": name,
                    "description": "",
                    "tone": "",
                    "is_builtin": name in built_in,
                })
        return styles

    def get_style(self, name: str) -> dict[str, Any]:
        """Load a style template by name.

        Args:
            name: Style name (built-in or custom file).

        Returns:
            Full style template as dict.

        Raises:
            ValueError: If style not found.
        """
        template = self._manager.load(name)
        return {
            "name": template.name,
            "description": template.description,
            "guidelines": template.guidelines,
            "vocabulary": template.vocabulary,
            "tone": template.tone,
            "examples": [
                {"chinese": ex["chinese"], "vietnamese": ex["vietnamese"]}
                if isinstance(ex, dict)
                else {"chinese": ex.chinese, "vietnamese": ex.vietnamese}
                for ex in (template.examples or [])
            ],
        }

    def get_style_names(self) -> list[str]:
        """Return list of all available style names."""
        return self._manager.list_available()
