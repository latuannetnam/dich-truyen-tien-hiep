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

        Args:
            updates: Nested dict matching get_settings() structure.
                     Only provided keys are updated.

        Returns:
            Updated full settings dict.
        """
        env_vars: dict[str, str] = {}

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

        for section, values in updates.items():
            if not isinstance(values, dict):
                continue
            prefix = section_prefix_map.get(section, "")
            for key, value in values.items():
                # Skip masked API keys (user didn't change them)
                if key == "api_key" and isinstance(value, str) and "••" in value:
                    continue
                env_name = f"{prefix}{key.upper()}"
                env_vars[env_name] = str(value)

        # Write to .env file
        self._update_env_file(env_vars)

        # Update environment and reload config
        for name, value in env_vars.items():
            os.environ[name] = value
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

    def _update_env_file(self, env_vars: dict[str, str]) -> None:
        """Update .env file, preserving existing entries.

        Handles quoted values (KEY="value" or KEY='value') correctly.
        Preserves comments and blank lines.
        """
        lines: list[str] = []
        existing_keys: set[str] = set()

        if self._env_file.exists():
            for line in self._env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in env_vars:
                        lines.append(f"{key}={env_vars[key]}")
                        existing_keys.add(key)
                        continue
                lines.append(line)

        # Add new keys
        for key, value in env_vars.items():
            if key not in existing_keys:
                lines.append(f"{key}={value}")

        self._env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _strip_quotes(value: str) -> str:
        """Strip surrounding quotes from .env values."""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            return value[1:-1]
        return value
