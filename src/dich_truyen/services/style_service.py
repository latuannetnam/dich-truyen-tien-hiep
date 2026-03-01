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
            List of dicts with 'name', 'description', 'tone', 'is_builtin', and 'style_type'.
        """
        styles: list[dict[str, Any]] = []
        built_in = set(self._manager.get_built_in_names())

        for name in self._manager.list_available():
            try:
                template = self._manager.load(name)
                styles.append(
                    {
                        "name": template.name,
                        "description": template.description,
                        "tone": template.tone,
                        "is_builtin": name in built_in,
                        "style_type": self.get_style_type(name),
                    }
                )
            except Exception:
                styles.append(
                    {
                        "name": name,
                        "description": "",
                        "tone": "",
                        "is_builtin": name in built_in,
                        "style_type": "custom",
                    }
                )
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

    def duplicate_style(self, name: str, new_name: str | None = None) -> dict[str, Any]:
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
        """Validate and parse a YAML string into a style dict (does NOT save).

        The caller should use create_style() to persist after user review.

        Args:
            yaml_content: YAML content string.

        Returns:
            Parsed style as dict (not saved to disk).

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
