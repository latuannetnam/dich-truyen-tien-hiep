"""Configuration service for web UI.

Provides read/write access to app configuration. Reads from the in-memory
AppConfig and writes changes back to the .env file so CLI picks them up too.
"""

import os
from pathlib import Path
from typing import Any, Optional

from dich_truyen.config import AppConfig, get_config, set_config


class ConfigService:
    """Read and update application configuration.

    Updates are written to .env for persistence. The in-memory config
    is also refreshed so the running server picks up changes immediately.
    """

    def __init__(self, env_file: Optional[Path] = None) -> None:
        self._env_file = env_file or Path(".env")

    def get_settings(self) -> dict[str, Any]:
        """Get current configuration as a nested dict.

        Reloads from .env on every call so the UI always reflects
        the actual file contents.

        Returns:
            Dict with all configuration sections.
            API keys are masked for security.
        """
        # Always reload from .env so we pick up external edits
        set_config(AppConfig.load(self._env_file))
        config = get_config()
        return {
            "llm": {
                "api_key": self._mask_key_optional(config.llm.api_key),
                "base_url": config.llm.base_url,
                "model": config.llm.model,
                "max_tokens": config.llm.max_tokens,
                "temperature": config.llm.temperature,
            },
            "crawler": {
                "delay_ms": config.crawler.delay_ms,
                "max_retries": config.crawler.max_retries,
                "timeout_seconds": config.crawler.timeout_seconds,
                "user_agent": config.crawler.user_agent,
            },
            "translation": {
                "chunk_size": config.translation.chunk_size,
                "chunk_overlap": config.translation.chunk_overlap,
                "progressive_glossary": config.translation.progressive_glossary,
                "enable_glossary_annotation": config.translation.enable_glossary_annotation,
                "enable_state_tracking": config.translation.enable_state_tracking,
                "state_tracking_max_retries": config.translation.state_tracking_max_retries,
                "glossary_sample_chapters": config.translation.glossary_sample_chapters,
                "glossary_sample_size": config.translation.glossary_sample_size,
                "glossary_min_entries": config.translation.glossary_min_entries,
                "glossary_max_entries": config.translation.glossary_max_entries,
                "glossary_random_sample": config.translation.glossary_random_sample,
                "enable_polish_pass": config.translation.enable_polish_pass,
                "polish_temperature": config.translation.polish_temperature,
                "polish_max_retries": config.translation.polish_max_retries,
            },
            "pipeline": {
                "translator_workers": config.pipeline.translator_workers,
                "queue_size": config.pipeline.queue_size,
                "crawl_delay_ms": config.pipeline.crawl_delay_ms,
                "glossary_wait_timeout": config.pipeline.glossary_wait_timeout,
                "glossary_batch_interval": config.pipeline.glossary_batch_interval,
                "glossary_scorer_rebuild_threshold": config.pipeline.glossary_scorer_rebuild_threshold,
            },
            "export": {
                "parallel_workers": config.export.parallel_workers,
                "volume_size": config.export.volume_size,
                "fast_mode": config.export.fast_mode,
            },
            "calibre": {
                "path": config.calibre.path,
            },
            "crawler_llm": {
                "api_key": self._mask_key_optional(config.crawler_llm.api_key),
                "base_url": config.crawler_llm.base_url,
                "model": config.crawler_llm.model,
                "max_tokens": config.crawler_llm.max_tokens,
                "temperature": config.crawler_llm.temperature,
            },
            "glossary_llm": {
                "api_key": self._mask_key_optional(config.glossary_llm.api_key),
                "base_url": config.glossary_llm.base_url,
                "model": config.glossary_llm.model,
                "max_tokens": config.glossary_llm.max_tokens,
                "temperature": config.glossary_llm.temperature,
            },
            "translator_llm": {
                "api_key": self._mask_key_optional(config.translator_llm.api_key),
                "base_url": config.translator_llm.base_url,
                "model": config.translator_llm.model,
                "max_tokens": config.translator_llm.max_tokens,
                "temperature": config.translator_llm.temperature,
            },
        }

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update configuration from a partial dict.

        Only values that differ from Pydantic defaults are written to .env.
        Values matching defaults are commented out (prefixed with #) for reference.

        Args:
            updates: Nested dict matching get_settings() structure.
                     Only provided keys are updated.

        Returns:
            Updated full settings dict.
        """
        defaults = self._get_defaults()

        # Map nested dict keys to env var names
        section_prefix_map = {
            "llm": "OPENAI_",
            "crawler": "CRAWLER_",
            "translation": "TRANSLATION_",
            "pipeline": "PIPELINE_",
            "export": "EXPORT_",
            "calibre": "CALIBRE_",
            "crawler_llm": "CRAWLER_LLM_",
            "glossary_llm": "GLOSSARY_LLM_",
            "translator_llm": "TRANSLATOR_LLM_",
        }

        write_vars: dict[str, str] = {}  # Non-default values to write
        comment_vars: set[str] = set()   # Default values to comment out

        for section, values in updates.items():
            if not isinstance(values, dict):
                continue
            prefix = section_prefix_map.get(section, "")
            section_defaults = defaults.get(section, {})

            for key, value in values.items():
                # Skip masked API keys (user didn't change them)
                if key == "api_key" and isinstance(value, str) and "••" in value:
                    continue
                env_name = f"{prefix}{key.upper()}"
                default_value = section_defaults.get(key)

                # Compare value against default
                if self._is_default(value, default_value):
                    comment_vars.add(env_name)
                else:
                    write_vars[env_name] = str(value)

        # Write to .env file
        self._update_env_file(write_vars, comment_vars)

        # Update environment: set non-default vars, remove defaults
        for name, value in write_vars.items():
            os.environ[name] = value
        for name in comment_vars:
            os.environ.pop(name, None)
        set_config(AppConfig.load(self._env_file))

        return self.get_settings()

    def _get_defaults(self) -> dict[str, dict[str, Any]]:
        """Build a map of all Pydantic Field default values.

        Uses model_fields metadata to get the true defaults defined in
        Field(..., default=X), NOT from environment variables.
        """
        from pydantic.fields import FieldInfo

        from dich_truyen.config import (
            CalibreConfig,
            CrawlerConfig,
            CrawlerLLMConfig,
            ExportConfig,
            GlossaryLLMConfig,
            LLMConfig,
            PipelineConfig,
            TranslationConfig,
            TranslatorLLMConfig,
        )

        def _field_defaults(model_cls: type) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for name, field_info in model_cls.model_fields.items():
                if isinstance(field_info, FieldInfo) and field_info.default is not None:
                    result[name] = field_info.default
            return result

        return {
            "llm": _field_defaults(LLMConfig),
            "crawler": _field_defaults(CrawlerConfig),
            "translation": _field_defaults(TranslationConfig),
            "pipeline": _field_defaults(PipelineConfig),
            "export": _field_defaults(ExportConfig),
            "calibre": _field_defaults(CalibreConfig),
            "crawler_llm": _field_defaults(CrawlerLLMConfig),
            "glossary_llm": _field_defaults(GlossaryLLMConfig),
            "translator_llm": _field_defaults(TranslatorLLMConfig),
        }

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

    def _update_env_file(
        self, write_vars: dict[str, str], comment_vars: set[str] | None = None
    ) -> None:
        """Update .env file, preserving existing entries.

        - write_vars: keys to set with new values
        - comment_vars: keys to comment out (value matches default)
        Handles commented-out lines: if a key was previously commented,
        it gets uncommented when set to a non-default value.
        """
        # Backup before modifying
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
                        # Comment out: value matches default
                        lines.append(f"# {stripped}")
                        handled_keys.add(key)
                        continue

                # Check commented-out lines: # KEY=value
                if stripped.startswith("#") and "=" in stripped:
                    uncommented = stripped.lstrip("#").strip()
                    key = uncommented.split("=", 1)[0].strip()
                    if key in write_vars:
                        # Uncomment and set new value
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
