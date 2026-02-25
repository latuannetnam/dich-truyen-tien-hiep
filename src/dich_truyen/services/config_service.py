"""Configuration service for web UI.

Provides read/write access to app configuration. Reads from the in-memory
AppConfig and writes changes back to the .env file so CLI picks them up too.
"""

import os
from pathlib import Path
from typing import Any, Optional

from pydantic.fields import FieldInfo

from dich_truyen.config import SECTIONS, AppConfig, get_config, set_config


class ConfigService:
    """Read and update application configuration.

    Uses the SECTIONS registry from config.py so adding a new config field
    only requires editing the Pydantic model — no changes needed here.

    Updates are written to .env for persistence. The in-memory config
    is also refreshed so the running server picks up changes immediately.
    """

    def __init__(self, env_file: Optional[Path] = None) -> None:
        self._env_file = env_file or Path(".env")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_settings(self) -> dict[str, Any]:
        """Get current configuration as a nested dict.

        Auto-generated from SECTIONS registry — no manual field listing.
        Reloads from .env on every call so the UI always reflects the file.
        API keys are masked for security.
        Includes _descriptions extracted from Pydantic Field metadata.
        """
        set_config(AppConfig.load(self._env_file))
        config = get_config()

        result: dict[str, Any] = {}
        descriptions: dict[str, dict[str, str]] = {}
        for section_key, attr_name in SECTIONS.items():
            sub = getattr(config, attr_name)
            data = sub.model_dump()
            # Mask api_key if present
            if "api_key" in data:
                data["api_key"] = self._mask_key_optional(data["api_key"])
            result[section_key] = data
            # Extract field descriptions
            section_desc: dict[str, str] = {}
            for name, field_info in type(sub).model_fields.items():
                if field_info.description:
                    section_desc[name] = field_info.description
            descriptions[section_key] = section_desc

        result["_descriptions"] = descriptions
        return result

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update configuration from a partial dict.

        Only values that differ from Pydantic defaults are written to .env.
        Values matching defaults are commented out (prefixed with #) for reference.
        """
        defaults = self._get_defaults()
        prefix_map = self._get_prefix_map()

        write_vars: dict[str, str] = {}  # Non-default values to write
        comment_vars: set[str] = set()   # Default values to comment out

        for section, values in updates.items():
            if not isinstance(values, dict):
                continue
            # Skip metadata keys (e.g. _descriptions) and unknown sections
            if section.startswith("_") or section not in prefix_map:
                continue
            prefix = prefix_map[section]
            section_defaults = defaults.get(section, {})

            for key, value in values.items():
                # Skip masked API keys (user didn't change them)
                if key == "api_key" and isinstance(value, str) and "••" in value:
                    continue
                env_name = f"{prefix}{key.upper()}"
                default_value = section_defaults.get(key)

                if self._is_default(value, default_value):
                    comment_vars.add(env_name)
                else:
                    write_vars[env_name] = str(value)

        self._update_env_file(write_vars, comment_vars)

        # Update environment: set non-default vars, remove defaults
        for name, value in write_vars.items():
            os.environ[name] = value
        for name in comment_vars:
            os.environ.pop(name, None)
        set_config(AppConfig.load(self._env_file))

        return self.get_settings()

    def test_connection(self) -> dict[str, Any]:
        """Test LLM API connection.

        Returns:
            Dict with 'success' bool and 'message' string.
        """
        config = get_config()
        if not config.llm.api_key:
            return {"success": False, "message": "API key is not configured"}

        try:
            import httpx

            response = httpx.get(
                f"{config.llm.base_url}/models",
                headers={"Authorization": f"Bearer {config.llm.api_key}"},
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            return {
                "success": False,
                "message": f"API returned {response.status_code}",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Internals — auto-derived from model metadata
    # ------------------------------------------------------------------

    def _get_prefix_map(self) -> dict[str, str]:
        """Auto-derive section → env_prefix map from Pydantic models."""
        config = get_config()
        result: dict[str, str] = {}
        for section_key, attr_name in SECTIONS.items():
            sub = getattr(config, attr_name)
            mc = sub.model_config if hasattr(sub, "model_config") else {}
            result[section_key] = mc.get("env_prefix", "")
        return result

    def _get_defaults(self) -> dict[str, dict[str, Any]]:
        """Build a map of all Pydantic Field default values.

        Uses model_fields metadata to get the true defaults defined in
        Field(..., default=X), NOT from environment variables.
        """
        config = get_config()
        result: dict[str, dict[str, Any]] = {}
        for section_key, attr_name in SECTIONS.items():
            sub = getattr(config, attr_name)
            field_defaults: dict[str, Any] = {}
            for name, field_info in type(sub).model_fields.items():
                if isinstance(field_info, FieldInfo) and field_info.default is not None:
                    field_defaults[name] = field_info.default
            result[section_key] = field_defaults
        return result

    @staticmethod
    def _is_default(value: Any, default: Any) -> bool:
        """Check if a value matches its default."""
        if default is None:
            return False  # Unknown default, always save
        # Handle boolean comparison (frontend may send string "true"/"false")
        if isinstance(default, bool):
            if isinstance(value, bool):
                return value == default
            return str(value).lower() == str(default).lower()
        # Handle numeric comparison (avoid str(0) != str(0.0) mismatch)
        if isinstance(default, (int, float)):
            try:
                return float(value) == float(default)
            except (ValueError, TypeError):
                pass
        # Fallback: string comparison
        return str(value) == str(default)

    # ------------------------------------------------------------------
    # Key masking
    # ------------------------------------------------------------------

    def _mask_key(self, key: str) -> str:
        """Mask API key for display."""
        if not key or len(key) < 8:
            return "••••••••"
        return key[:4] + "••••" + key[-4:]

    def _mask_key_optional(self, key: str) -> str:
        """Mask API key for optional/override fields.

        Returns empty string when key is not set, so the frontend
        can show a placeholder like '(use default)'.
        """
        if not key:
            return ""
        if len(key) < 8:
            return "••••••••"
        return key[:4] + "••••" + key[-4:]

    # ------------------------------------------------------------------
    # .env file management
    # ------------------------------------------------------------------

    def _update_env_file(
        self, write_vars: dict[str, str], comment_vars: set[str] | None = None
    ) -> None:
        """Update .env file, preserving existing entries.

        - write_vars: keys to set with new values
        - comment_vars: keys to comment out (value matches default)
        Handles commented-out lines: if a key was previously commented,
        it gets uncommented when set to a non-default value.
        """
        self._backup_env_file()

        comment_vars = comment_vars or set()
        lines: list[str] = []
        handled_keys: set[str] = set()

        if self._env_file.exists():
            for line in self._env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()

                # Check active (uncommented) KEY=value lines
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in write_vars:
                        lines.append(f"{key}={write_vars[key]}")
                        handled_keys.add(key)
                        continue
                    if key in comment_vars:
                        lines.append(f"# {stripped}")
                        handled_keys.add(key)
                        continue

                # Check commented-out lines: # KEY=value
                if stripped.startswith("#") and "=" in stripped:
                    uncommented = stripped.lstrip("#").strip()
                    key = uncommented.split("=", 1)[0].strip()
                    if key in write_vars:
                        lines.append(f"{key}={write_vars[key]}")
                        handled_keys.add(key)
                        continue

                lines.append(line)

        # Add new keys that weren't in the file at all
        for key, value in write_vars.items():
            if key not in handled_keys:
                lines.append(f"{key}={value}")

        self._env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _MAX_BACKUPS = 5

    def _backup_env_file(self) -> None:
        """Create a rotating backup of .env before modifying it.

        Keeps up to _MAX_BACKUPS copies: .env.bak.1 (newest) to .env.bak.5 (oldest).
        """
        import shutil

        if not self._env_file.exists():
            return

        # Rotate existing backups: .bak.4 → .bak.5, .bak.3 → .bak.4, ...
        for i in range(self._MAX_BACKUPS, 1, -1):
            older = self._env_file.parent / f"{self._env_file.name}.bak.{i}"
            newer = self._env_file.parent / f"{self._env_file.name}.bak.{i - 1}"
            if newer.exists():
                shutil.copy2(str(newer), str(older))

        # Copy current .env → .env.bak.1
        bak_1 = self._env_file.parent / f"{self._env_file.name}.bak.1"
        shutil.copy2(str(self._env_file), str(bak_1))

    @staticmethod
    def _strip_quotes(value: str) -> str:
        """Strip surrounding quotes from .env values."""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            return value[1:-1]
        return value
