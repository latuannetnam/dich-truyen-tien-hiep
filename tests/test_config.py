"""Tests for application configuration loading."""

from dich_truyen.config import AppConfig


def test_explicit_env_file_overrides_existing_environment(tmp_path, monkeypatch):
    """Explicit env files should refresh values inherited from the shell."""
    monkeypatch.setenv("TRANSLATION_CHUNK_SIZE", "2000")
    env_file = tmp_path / ".env"
    env_file.write_text("TRANSLATION_CHUNK_SIZE=4000\n", encoding="utf-8")

    config = AppConfig.load(env_file=env_file)

    assert config.translation.chunk_size == 4000
