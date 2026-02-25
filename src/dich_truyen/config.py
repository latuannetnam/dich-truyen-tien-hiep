"""Configuration management with environment variables and CLI overrides."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------------------------
# Sub-config models
# ---------------------------------------------------------------------------


class LLMConfig(BaseSettings):
    """LLM/OpenAI configuration."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: str = Field(default="", description="OpenAI API key")
    base_url: str = Field(default="https://api.openai.com/v1", description="API base URL")
    model: str = Field(default="gpt-4.1", description="Model name")
    max_tokens: int = Field(default=4096, description="Max tokens per request")
    temperature: float = Field(default=0.7, description="Temperature for generation")


class TaskLLMConfig(BaseSettings):
    """Base class for task-specific LLM overrides.

    Empty fields fall back to the default LLM config.
    """

    api_key: str = Field(default="", description="API key")
    base_url: str = Field(default="", description="API base URL")
    model: str = Field(default="", description="Model name")
    max_tokens: int = Field(default=0, description="Max tokens per request")
    temperature: float = Field(default=0.0, description="Temperature")


class CrawlerLLMConfig(TaskLLMConfig):
    """LLM configuration for crawler/pattern discovery."""

    model_config = SettingsConfigDict(env_prefix="CRAWLER_LLM_")


class GlossaryLLMConfig(TaskLLMConfig):
    """LLM configuration for glossary generation."""

    model_config = SettingsConfigDict(env_prefix="GLOSSARY_LLM_")


class TranslatorLLMConfig(TaskLLMConfig):
    """LLM configuration for translation."""

    model_config = SettingsConfigDict(env_prefix="TRANSLATOR_LLM_")


class CrawlerConfig(BaseSettings):
    """Crawler configuration."""

    model_config = SettingsConfigDict(env_prefix="CRAWLER_")

    delay_ms: int = Field(default=1000, description="Delay between HTTP requests in ms (rate limiting)")
    max_retries: int = Field(default=3, description="Max retry attempts")
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User agent string",
    )


class TranslationConfig(BaseSettings):
    """Translation configuration."""

    model_config = SettingsConfigDict(env_prefix="TRANSLATION_")

    chunk_size: int = Field(default=2000, description="Characters per translation chunk")
    chunk_overlap: int = Field(default=300, description="Overlap characters for context")
    progressive_glossary: bool = Field(
        default=True, description="Extract new terms during translation"
    )

    # Quality enhancement features
    enable_glossary_annotation: bool = Field(
        default=True, description="Annotate source text with glossary terms"
    )
    enable_state_tracking: bool = Field(
        default=True, description="Track narrative state across chunks"
    )
    state_tracking_max_retries: int = Field(
        default=2, description="Max retries for state extraction before disabling"
    )

    # Glossary generation settings
    glossary_sample_chapters: int = Field(
        default=5, description="Number of chapters to sample for glossary"
    )
    glossary_sample_size: int = Field(
        default=3000, description="Characters to take from each sample chapter"
    )
    glossary_min_entries: int = Field(
        default=20, description="Minimum glossary entries to generate"
    )
    glossary_max_entries: int = Field(default=100, description="Maximum glossary entries to keep")
    glossary_random_sample: bool = Field(
        default=True, description="Randomly select sample chapters"
    )

    # Two-pass translation (Editor-in-Chief)
    enable_polish_pass: bool = Field(
        default=True, description="Enable second pass for polishing translation"
    )
    polish_temperature: float = Field(
        default=0.4, description="Temperature for polish pass (lower = more conservative edits)"
    )
    polish_max_retries: int = Field(
        default=1, description="Max retries for polish pass before falling back to draft"
    )


class CalibreConfig(BaseSettings):
    """Calibre configuration."""

    model_config = SettingsConfigDict(env_prefix="CALIBRE_")

    path: str = Field(default="ebook-convert", description="Path to ebook-convert")


class ExportConfig(BaseSettings):
    """Export configuration."""

    model_config = SettingsConfigDict(env_prefix="EXPORT_")

    parallel_workers: int = Field(default=8, description="Max threads for parallel file writing")
    volume_size: int = Field(default=0, description="Chapters per volume (0=single book)")
    fast_mode: bool = Field(default=True, description="Use direct EPUB assembly for speed")


class PipelineConfig(BaseSettings):
    """Streaming pipeline configuration."""

    model_config = SettingsConfigDict(env_prefix="PIPELINE_")

    translator_workers: int = Field(
        default=3, description="Number of parallel translation workers"
    )
    queue_size: int = Field(
        default=10, description="Max chapters buffered between crawl and translate"
    )
    crawl_delay_ms: int = Field(
        default=1000, description="Delay between chapter downloads in streaming pipeline in ms"
    )

    # Glossary sync settings
    glossary_wait_timeout: int = Field(
        default=60,
        description="Max seconds to wait for initial glossary before proceeding with empty",
    )
    glossary_batch_interval: int = Field(
        default=60, description="Seconds between batch progressive extraction runs"
    )
    glossary_scorer_rebuild_threshold: int = Field(
        default=5, description="Rebuild TF-IDF scorer every N version increments"
    )


# ---------------------------------------------------------------------------
# Main AppConfig with SECTIONS registry
# ---------------------------------------------------------------------------

# Maps section key → AppConfig attribute name.
# ConfigService uses this to auto-generate serialization and prefix maps.
SECTIONS: dict[str, str] = {
    "llm": "llm",
    "crawler": "crawler",
    "translation": "translation",
    "pipeline": "pipeline",
    "export": "export",
    "calibre": "calibre",
    "crawler_llm": "crawler_llm",
    "glossary_llm": "glossary_llm",
    "translator_llm": "translator_llm",
}


class AppConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    log_level: str = Field(default="INFO", description="Logging level")
    books_dir: Path = Field(default=Path("books"), description="Books output directory")

    # Sub-configs
    llm: LLMConfig = Field(default_factory=LLMConfig)
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    calibre: CalibreConfig = Field(default_factory=CalibreConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)

    # Task-specific LLM configs (fallback to llm if not set)
    crawler_llm: CrawlerLLMConfig = Field(default_factory=CrawlerLLMConfig)
    glossary_llm: GlossaryLLMConfig = Field(default_factory=GlossaryLLMConfig)
    translator_llm: TranslatorLLMConfig = Field(default_factory=TranslatorLLMConfig)

    @classmethod
    def load(cls, env_file: Optional[Path] = None) -> "AppConfig":
        """Load configuration from environment and .env file."""
        from dotenv import load_dotenv

        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            # Try to find .env in current directory or parent directories
            load_dotenv()

        return cls(
            llm=LLMConfig(),
            crawler=CrawlerConfig(),
            translation=TranslationConfig(),
            calibre=CalibreConfig(),
            crawler_llm=CrawlerLLMConfig(),
            glossary_llm=GlossaryLLMConfig(),
            translator_llm=TranslatorLLMConfig(),
        )


# ---------------------------------------------------------------------------
# Global config singleton
# ---------------------------------------------------------------------------

_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def set_config(config: AppConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


# ---------------------------------------------------------------------------
# LLM config helpers
# ---------------------------------------------------------------------------


def get_effective_llm_config(
    specific: TaskLLMConfig,
    fallback: LLMConfig,
    task_name: Optional[str] = None,
) -> LLMConfig:
    """Merge specific LLM config with fallback for unset values.

    This allows task-specific configs (crawler_llm, glossary_llm, translator_llm)
    to override only the values they set, falling back to the default llm config.

    Args:
        specific: Task-specific config (CrawlerLLMConfig, GlossaryLLMConfig, etc.)
        fallback: Default LLMConfig to use for unset values
        task_name: Optional task name for detailed logging (e.g., "Crawler", "Glossary")

    Returns:
        LLMConfig with merged values
    """
    effective = LLMConfig(
        api_key=specific.api_key or fallback.api_key,
        base_url=specific.base_url or fallback.base_url,
        model=specific.model or fallback.model,
        max_tokens=specific.max_tokens or fallback.max_tokens,
        temperature=specific.temperature if specific.temperature > 0 else fallback.temperature,
    )

    if task_name:
        console = Console()
        console.print(f"[blue]  {task_name} LLM Config:[/blue]")
        _fields = [
            ("Model", "model", specific.model),
            ("API Key", None, specific.api_key),
            ("Base URL", "base_url", specific.base_url),
            ("Max Tokens", "max_tokens", specific.max_tokens),
            ("Temperature", None, specific.temperature),
        ]
        for label, attr, spec_val in _fields:
            val = getattr(effective, attr) if attr else None
            is_specific = bool(spec_val) if label != "Temperature" else spec_val > 0
            source = "(specific)" if is_specific else "(from default)"
            if label == "API Key":
                display = (
                    effective.api_key[:8] + "..."
                    if len(effective.api_key) > 8
                    else "***"
                )
                console.print(f"[blue]    • {label}: {display} {source}[/blue]")
            elif label == "Temperature":
                console.print(
                    f"[blue]    • {label}: {effective.temperature} {source}[/blue]"
                )
            else:
                console.print(f"[blue]    • {label}: {val} {source}[/blue]")

    return effective


def log_llm_config_summary() -> None:
    """Log a summary table of all LLM configurations.

    Shows default config and any task-specific overrides in a clear table format.
    """
    console = Console()
    app_config = get_config()

    console.print("\n[bold blue]=== LLM Configuration ===[/bold blue]")

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Task", style="cyan", width=12)
    table.add_column("Model", style="green")
    table.add_column("Base URL", style="yellow")
    table.add_column("Max Tokens", style="magenta", justify="right")
    table.add_column("Temperature", style="magenta", justify="right")
    table.add_column("Source", style="dim")

    # Default config
    table.add_row(
        "Default",
        app_config.llm.model,
        app_config.llm.base_url,
        str(app_config.llm.max_tokens),
        str(app_config.llm.temperature),
        "OPENAI_*",
    )

    # Task-specific configs
    task_configs: list[tuple[str, TaskLLMConfig]] = [
        ("Crawler", app_config.crawler_llm),
        ("Glossary", app_config.glossary_llm),
        ("Translator", app_config.translator_llm),
    ]

    for task_name, task_cfg in task_configs:
        has_override = bool(task_cfg.model or task_cfg.api_key)
        if has_override:
            effective = get_effective_llm_config(task_cfg, app_config.llm)
            source = f"{task_name.upper()}_LLM_*" if task_cfg.model else "OPENAI_* (fallback)"
            table.add_row(
                task_name,
                effective.model,
                effective.base_url,
                str(effective.max_tokens),
                str(effective.temperature),
                source,
            )
        else:
            table.add_row(
                task_name,
                app_config.llm.model,
                app_config.llm.base_url,
                str(app_config.llm.max_tokens),
                str(app_config.llm.temperature),
                "OPENAI_* (fallback)",
            )

    console.print(table)
    console.print()
