"""Unit tests for the translation module."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from dich_truyen.translator.glossary import Glossary, GlossaryEntry
from dich_truyen.translator.style import (
    StyleTemplate,
    StyleManager,
    BUILT_IN_STYLES,
    TIEN_HIEP_STYLE,
    KIEM_HIEP_STYLE,
)
from dich_truyen.translator.engine import TranslationEngine
from dich_truyen.translator.llm import LLMClient
from dich_truyen.config import LLMConfig, TranslationConfig


class TestGlossaryEntry:
    """Test GlossaryEntry model."""

    def test_create_entry(self):
        """Test creating a glossary entry."""
        entry = GlossaryEntry(
            chinese="陈平安",
            vietnamese="Trần Bình An",
            category="character",
            notes="Main protagonist",
        )
        assert entry.chinese == "陈平安"
        assert entry.vietnamese == "Trần Bình An"
        assert entry.category == "character"

    def test_default_category(self):
        """Test default category is 'general'."""
        entry = GlossaryEntry(chinese="测试", vietnamese="thử nghiệm")
        assert entry.category == "general"


class TestGlossary:
    """Test Glossary class."""

    def test_create_empty_glossary(self):
        """Test creating empty glossary."""
        glossary = Glossary()
        assert len(glossary) == 0

    def test_add_entry(self):
        """Test adding entries."""
        glossary = Glossary()
        entry = GlossaryEntry(chinese="剑", vietnamese="kiếm", category="item")
        glossary.add(entry)
        assert len(glossary) == 1
        assert "剑" in glossary

    def test_lookup(self):
        """Test looking up entries."""
        glossary = Glossary()
        entry = GlossaryEntry(chinese="剑", vietnamese="kiếm", category="item")
        glossary.add(entry)

        result = glossary.lookup("剑")
        assert result is not None
        assert result.vietnamese == "kiếm"

        result = glossary.lookup("刀")
        assert result is None

    def test_update_existing(self):
        """Test updating existing entry."""
        glossary = Glossary()
        glossary.add(GlossaryEntry(chinese="剑", vietnamese="kiếm v1"))
        glossary.add(GlossaryEntry(chinese="剑", vietnamese="kiếm v2"))

        assert len(glossary) == 1
        assert glossary.lookup("剑").vietnamese == "kiếm v2"

    def test_remove_entry(self):
        """Test removing entries."""
        glossary = Glossary()
        glossary.add(GlossaryEntry(chinese="剑", vietnamese="kiếm"))

        result = glossary.remove("剑")
        assert result is True
        assert len(glossary) == 0

        result = glossary.remove("刀")
        assert result is False

    def test_get_by_category(self):
        """Test filtering by category."""
        glossary = Glossary([
            GlossaryEntry(chinese="剑", vietnamese="kiếm", category="item"),
            GlossaryEntry(chinese="刀", vietnamese="đao", category="item"),
            GlossaryEntry(chinese="张三", vietnamese="Trương Tam", category="character"),
        ])

        items = glossary.get_by_category("item")
        assert len(items) == 2

        characters = glossary.get_by_category("character")
        assert len(characters) == 1

    def test_to_prompt_format(self):
        """Test formatting for LLM prompt."""
        glossary = Glossary([
            GlossaryEntry(chinese="陈平安", vietnamese="Trần Bình An", category="character"),
            GlossaryEntry(chinese="练气境", vietnamese="Luyện Khí cảnh", category="realm"),
        ])

        prompt = glossary.to_prompt_format()
        assert "Trần Bình An" in prompt
        assert "Luyện Khí cảnh" in prompt
        assert "Nhân vật" in prompt
        assert "Cảnh giới" in prompt

    def test_csv_export_import(self, tmp_path):
        """Test CSV export and import."""
        glossary = Glossary([
            GlossaryEntry(chinese="剑", vietnamese="kiếm", category="item"),
            GlossaryEntry(chinese="张三", vietnamese="Trương Tam", category="character"),
        ])

        csv_path = tmp_path / "glossary.csv"
        glossary.to_csv(csv_path)
        assert csv_path.exists()

        loaded = Glossary.from_csv(csv_path)
        assert len(loaded) == 2
        assert loaded.lookup("剑").vietnamese == "kiếm"

    def test_save_and_load(self, tmp_path):
        """Test saving and loading from book directory."""
        glossary = Glossary([
            GlossaryEntry(chinese="剑", vietnamese="kiếm"),
        ])

        glossary.save(tmp_path)
        assert (tmp_path / "glossary.csv").exists()

        loaded = Glossary.load(tmp_path)
        assert loaded is not None
        assert len(loaded) == 1


class TestStyleTemplate:
    """Test StyleTemplate class."""

    def test_create_style(self):
        """Test creating a style template."""
        style = StyleTemplate(
            name="test_style",
            description="Test style",
            guidelines=["Rule 1", "Rule 2"],
            vocabulary={"我": "ta"},
            tone="formal",
        )
        assert style.name == "test_style"
        assert len(style.guidelines) == 2

    def test_to_prompt_format(self):
        """Test formatting for LLM prompt."""
        style = StyleTemplate(
            name="test",
            description="Test style",
            guidelines=["Use formal language"],
            vocabulary={"我": "ta"},
            examples=[{"chinese": "你好", "vietnamese": "Xin chào"}],
        )

        prompt = style.to_prompt_format()
        assert "Test style" in prompt
        assert "Use formal language" in prompt
        assert "我 → ta" in prompt
        assert "你好" in prompt

    def test_yaml_export_import(self, tmp_path):
        """Test YAML export and import."""
        style = StyleTemplate(
            name="test",
            description="Test style",
            guidelines=["Rule 1"],
        )

        yaml_path = tmp_path / "test.yaml"
        style.to_yaml(yaml_path)
        assert yaml_path.exists()

        loaded = StyleTemplate.from_yaml(yaml_path)
        assert loaded.name == "test"
        assert loaded.description == "Test style"


class TestBuiltInStyles:
    """Test built-in style templates."""

    def test_tien_hiep_style_exists(self):
        """Test tiên hiệp style is defined."""
        assert "tien_hiep" in BUILT_IN_STYLES
        style = TIEN_HIEP_STYLE
        assert style.name == "tien_hiep"
        assert len(style.vocabulary) > 0
        assert len(style.guidelines) > 0

    def test_kiem_hiep_style_exists(self):
        """Test kiếm hiệp style is defined."""
        assert "kiem_hiep" in BUILT_IN_STYLES
        style = KIEM_HIEP_STYLE
        assert style.name == "kiem_hiep"
        assert "江湖" in style.vocabulary

    def test_all_built_in_styles(self):
        """Test all expected built-in styles exist."""
        expected = ["tien_hiep", "kiem_hiep", "huyen_huyen", "do_thi"]
        for name in expected:
            assert name in BUILT_IN_STYLES
            style = BUILT_IN_STYLES[name]
            assert style.name == name
            assert style.description != ""


class TestStyleManager:
    """Test StyleManager class."""

    def test_list_available(self):
        """Test listing available styles."""
        manager = StyleManager()
        styles = manager.list_available()
        assert "tien_hiep" in styles
        assert "kiem_hiep" in styles

    def test_load_built_in(self):
        """Test loading built-in style."""
        manager = StyleManager()
        style = manager.load("tien_hiep")
        assert style.name == "tien_hiep"

    def test_load_not_found(self):
        """Test loading non-existent style."""
        manager = StyleManager()
        with pytest.raises(ValueError, match="not found"):
            manager.load("nonexistent_style")

    def test_load_custom_yaml(self, tmp_path):
        """Test loading custom YAML style."""
        # Create custom style file
        custom_style = StyleTemplate(
            name="custom",
            description="Custom style",
            guidelines=["Custom rule"],
        )
        (tmp_path / "custom.yaml").write_text(
            custom_style.model_dump_json(),
            encoding="utf-8",
        )

        # Actually write as YAML
        custom_style.to_yaml(tmp_path / "custom.yaml")

        manager = StyleManager(styles_dir=tmp_path)
        styles = manager.list_available()
        assert "custom" in styles

        loaded = manager.load("custom")
        assert loaded.name == "custom"


class TestTranslationEngine:
    """Test TranslationEngine class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return TranslationConfig(chunk_size=500)

    @pytest.fixture
    def engine(self, config):
        """Create test engine."""
        return TranslationEngine(
            style=TIEN_HIEP_STYLE,
            glossary=Glossary(),
            config=config,
        )

    def test_chunk_short_text(self, engine):
        """Test chunking short text."""
        text = "This is a short text."
        chunks = engine.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_by_paragraphs(self, engine):
        """Test chunking respects paragraph boundaries."""
        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        chunks = engine.chunk_text(text)
        # Should be one chunk as it's < 500 chars
        assert len(chunks) == 1

    def test_chunk_long_text(self, engine):
        """Test chunking long text."""
        # Create text longer than chunk size
        paragraphs = ["这是一个很长的段落。" * 50 for _ in range(5)]
        text = "\n\n".join(paragraphs)

        chunks = engine.chunk_text(text)
        assert len(chunks) > 1
        # Each chunk should be <= chunk_size (approximately)
        for chunk in chunks:
            # Allow some overflow for paragraph boundaries
            assert len(chunk) < engine.config.chunk_size * 2

    def test_chunk_preserves_content(self, engine):
        """Test chunking preserves all content."""
        text = "Line 1。\n\nLine 2。\n\nLine 3。"
        chunks = engine.chunk_text(text)
        combined = "\n\n".join(chunks)
        assert "Line 1" in combined
        assert "Line 2" in combined
        assert "Line 3" in combined


class TestLLMClient:
    """Test LLMClient class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return LLMConfig(
            api_key="test-key",
            base_url="https://api.test.com/v1",
            model="test-model",
        )

    def test_create_client(self, config):
        """Test creating LLM client."""
        client = LLMClient(config)
        assert client.config.api_key == "test-key"
        assert client.config.model == "test-model"

    def test_build_translation_prompts(self, config):
        """Test building translation prompts."""
        client = LLMClient(config)

        system = client._build_translation_system_prompt("Test style guidelines")
        assert "dịch giả" in system.lower() or "dịch" in system.lower()
        assert "Test style guidelines" in system

        user = client._build_translation_user_prompt(
            text="测试文本",
            glossary_prompt="glossary terms",
            context="previous context",
        )
        assert "测试文本" in user
        assert "glossary terms" in user
        assert "previous context" in user


# Integration tests (require API)
class TestTranslationIntegration:
    """Integration tests for translation (require OpenAI API)."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires OpenAI API key")
    async def test_translate_chunk(self):
        """Test translating a single chunk."""
        engine = TranslationEngine(
            style=TIEN_HIEP_STYLE,
            glossary=Glossary(),
        )

        result = await engine.translate_chunk("你好，世界！")
        assert len(result) > 0
        # Should be in Vietnamese
        assert any(c in result for c in "àáảãạăắằẳẵặâấầẩẫậ")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires OpenAI API key")
    async def test_generate_glossary(self):
        """Test generating glossary from samples."""
        from dich_truyen.translator.glossary import generate_glossary_from_samples

        samples = [
            "陈平安是一个年轻人。他来自小镇。",
            "练气境是修炼的第一个境界。",
        ]

        glossary = await generate_glossary_from_samples(samples)
        assert len(glossary) > 0
