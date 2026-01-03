"""Configuration management with environment variables and CLI overrides."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM/OpenAI configuration."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: str = Field(default="", description="OpenAI API key")
    base_url: str = Field(default="https://api.openai.com/v1", description="API base URL")
    model: str = Field(default="gpt-4o", description="Model name")
    max_tokens: int = Field(default=4096, description="Max tokens per request")
    temperature: float = Field(default=0.7, description="Temperature for generation")


class CrawlerConfig(BaseSettings):
    """Crawler configuration."""

    model_config = SettingsConfigDict(env_prefix="CRAWLER_")

    delay_ms: int = Field(default=1000, description="Delay between requests in ms")
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
    chunk_overlap: int = Field(default=300, description="Overlap characters for context in parallel mode")
    concurrent_requests: int = Field(default=3, description="Concurrent translation requests")
    progressive_glossary: bool = Field(default=True, description="Extract new terms during translation")
    
    # Glossary generation settings
    glossary_sample_chapters: int = Field(default=5, description="Number of chapters to sample for glossary")
    glossary_sample_size: int = Field(default=3000, description="Characters to take from each sample chapter")
    glossary_min_entries: int = Field(default=20, description="Minimum glossary entries to generate")
    glossary_max_entries: int = Field(default=100, description="Maximum glossary entries to keep")
    glossary_random_sample: bool = Field(default=True, description="Randomly select sample chapters")


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
        )


# Global config instance (lazy loaded)
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
