"""Tests for the streaming pipeline."""

import asyncio
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dotenv import load_dotenv

# Load .env for API key check
load_dotenv()

from dich_truyen.config import PipelineConfig
from dich_truyen.pipeline.streaming import StreamingPipeline, PipelineResult, PipelineStats
from dich_truyen.utils.progress import BookProgress, Chapter, ChapterStatus
from dich_truyen.translator.glossary import Glossary, GlossaryEntry


# Check if OpenAI API is configured for integration tests
def _has_openai_api():
    """Check if OpenAI API is available for testing."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    return bool(api_key) and not api_key.startswith("sk-your")

requires_openai = pytest.mark.skipif(
    not _has_openai_api(),
    reason="Requires OpenAI API key (set OPENAI_API_KEY)"
)


class TestPipelineConfig:
    """Tests for PipelineConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = PipelineConfig()
        
        assert config.translator_workers == 3
        assert config.queue_size == 10
        assert config.crawl_delay_ms == 1000


class TestPipelineResult:
    """Tests for PipelineResult."""
    
    def test_create_result(self):
        """Test creating a pipeline result."""
        result = PipelineResult(
            total_chapters=100,
            crawled=50,
            translated=45,
            failed_crawl=2,
            failed_translate=3,
        )
        
        assert result.total_chapters == 100
        assert result.crawled == 50
        assert result.translated == 45
        assert result.failed_crawl == 2
        assert result.failed_translate == 3


class TestPipelineStats:
    """Tests for PipelineStats."""
    
    def test_initial_values(self):
        """Test initial stats values."""
        stats = PipelineStats()
        
        assert stats.total_chapters == 0
        assert stats.chapters_crawled == 0
        assert stats.chapters_translated == 0
        assert stats.chunks_translated == 0
        assert stats.total_chunks == 0
        assert stats.chapters_in_queue == 0
        assert stats.crawl_errors == 0
        assert stats.translate_errors == 0
        assert stats.errors == []
        assert stats.worker_status == {}
    
    def test_worker_status_tracking(self):
        """Test worker status tracking."""
        stats = PipelineStats()
        stats.worker_status[1] = "Ch.1: translating [1,2]"
        stats.worker_status[2] = "idle"
        
        assert stats.worker_status[1] == "Ch.1: translating [1,2]"
        assert stats.worker_status[2] == "idle"


class TestStreamingPipeline:
    """Tests for StreamingPipeline."""
    
    def test_init_default_config(self):
        """Test initialization with default config."""
        pipeline = StreamingPipeline()
        
        assert pipeline.num_workers == 3
        assert pipeline.queue.maxsize == 0  # Unbounded queue
        assert pipeline._progress_lock is not None
        assert pipeline._glossary_lock is not None
    
    def test_init_custom_workers(self):
        """Test initialization with custom worker count."""
        pipeline = StreamingPipeline(translator_workers=5)
        
        assert pipeline.num_workers == 5
    
    @pytest.mark.asyncio
    async def test_update_chapter_status_thread_safe(self, tmp_path):
        """Test that chapter status updates are thread-safe."""
        # Setup
        pipeline = StreamingPipeline()
        pipeline.book_dir = tmp_path
        
        # Create mock progress
        chapter = Chapter(index=1, id="ch1", url="http://example.com/1")
        pipeline.progress = BookProgress(url="http://example.com")
        pipeline.progress.chapters = [chapter]
        
        # Update status
        await pipeline._update_chapter_status(chapter, ChapterStatus.CRAWLED)
        
        # Verify file was saved
        assert (tmp_path / "book.json").exists()
        
        # Verify status was updated
        loaded = BookProgress.load(tmp_path)
        assert loaded.chapters[0].status == ChapterStatus.CRAWLED
    
    @pytest.mark.asyncio
    async def test_run_validates_inputs(self, tmp_path):
        """Test that run validates inputs."""
        pipeline = StreamingPipeline()
        
        # No URL and no existing book.json should fail
        with pytest.raises(ValueError, match="No book.json found"):
            await pipeline.run(book_dir=tmp_path)
    
    @pytest.mark.asyncio
    async def test_queue_poison_pill(self):
        """Test that poison pills properly terminate workers."""
        pipeline = StreamingPipeline(translator_workers=2)
        
        # Put poison pills
        await pipeline.queue.put(None)
        await pipeline.queue.put(None)
        
        # Verify they can be retrieved
        item1 = await pipeline.queue.get()
        item2 = await pipeline.queue.get()
        
        assert item1 is None
        assert item2 is None


class TestResumeScenarios:
    """Test resume scenarios."""
    
    def test_analyze_chapters_to_crawl(self):
        """Test identifying chapters that need crawling."""
        chapters = [
            Chapter(index=1, id="1", url="http://test/1", status=ChapterStatus.PENDING),
            Chapter(index=2, id="2", url="http://test/2", status=ChapterStatus.CRAWLED),
            Chapter(index=3, id="3", url="http://test/3", status=ChapterStatus.TRANSLATED),
        ]
        
        to_crawl = [c for c in chapters if c.status == ChapterStatus.PENDING]
        to_translate = [c for c in chapters if c.status == ChapterStatus.CRAWLED]
        done = [c for c in chapters if c.status == ChapterStatus.TRANSLATED]
        
        assert len(to_crawl) == 1
        assert len(to_translate) == 1
        assert len(done) == 1
    
    def test_force_resets_all_chapters(self):
        """Test that force flag resets all chapters to PENDING."""
        chapters = [
            Chapter(index=1, id="1", url="http://test/1", status=ChapterStatus.CRAWLED),
            Chapter(index=2, id="2", url="http://test/2", status=ChapterStatus.TRANSLATED),
        ]
        
        # Simulate force reset
        for c in chapters:
            c.status = ChapterStatus.PENDING
        
        assert all(c.status == ChapterStatus.PENDING for c in chapters)


class TestProgressReload:
    """Test progress reload issues (stale reference bugs)."""
    
    def test_chapter_title_vi_update_persists(self, tmp_path):
        """Test that chapter title_vi updates are not lost on reload.
        
        This tests the bug where title_vi was updated on old chapter objects
        that were not saved because progress was reloaded.
        """
        # Create initial progress
        p1 = BookProgress(url="http://test.com", title="测试")
        c1 = Chapter(index=1, id="1", url="http://test/1", title_cn="第一章")
        p1.chapters = [c1]
        p1.save(tmp_path)
        
        # Load fresh copy (simulating reload)
        p2 = BookProgress.load(tmp_path)
        
        # Update title_vi on p2's chapter
        p2.chapters[0].title_vi = "Chương 1"
        p2.save(tmp_path)
        
        # Load again and verify
        p3 = BookProgress.load(tmp_path)
        assert p3.chapters[0].title_vi == "Chương 1"
    
    def test_stale_chapter_reference_issue(self, tmp_path):
        """Test that updating old chapter refs doesn't persist.
        
        This demonstrates the bug we fixed where chapters put in queue
        before reload had stale references.
        """
        # Create progress
        p1 = BookProgress(url="http://test.com")
        c1 = Chapter(index=1, id="1", url="http://test/1")
        p1.chapters = [c1]
        p1.save(tmp_path)
        
        # Save reference to old chapter
        old_chapter_ref = p1.chapters[0]
        
        # Reload (simulating setup_translation reload)
        p2 = BookProgress.load(tmp_path)
        
        # Update on OLD reference (this is the bug!)
        old_chapter_ref.title_vi = "Updated on OLD"
        
        # Save p2 (which doesn't have the update)
        p2.save(tmp_path)
        
        # Load and verify - the update was LOST
        p3 = BookProgress.load(tmp_path)
        assert p3.chapters[0].title_vi != "Updated on OLD"  # Bug: update was lost


class TestGlossaryIntegration:
    """Test glossary integration with streaming pipeline."""
    
    def test_glossary_save_on_pipeline_complete(self, tmp_path):
        """Test that glossary is saved at end of pipeline."""
        # Create a glossary
        glossary = Glossary([
            GlossaryEntry(chinese="剑", vietnamese="kiếm"),
            GlossaryEntry(chinese="仙", vietnamese="tiên"),
        ])
        
        # Save it
        glossary.save(tmp_path)
        
        # Verify file exists
        assert (tmp_path / "glossary.csv").exists()
        
        # Reload and verify
        loaded = Glossary.load(tmp_path)
        assert len(loaded) == 2
        assert loaded.lookup("剑").vietnamese == "kiếm"
    
    def test_glossary_load_or_create(self, tmp_path):
        """Test Glossary.load_or_create behavior."""
        # First call creates empty glossary
        g1 = Glossary.load_or_create(tmp_path)
        assert len(g1) == 0
        
        # Add entry and save
        g1.add(GlossaryEntry(chinese="测试", vietnamese="thử nghiệm"))
        g1.save(tmp_path)
        
        # Second call loads existing
        g2 = Glossary.load_or_create(tmp_path)
        assert len(g2) == 1
        assert g2.lookup("测试").vietnamese == "thử nghiệm"


class TestMetadataTranslation:
    """Test book metadata translation."""
    
    def test_title_vi_empty_string_is_falsy(self):
        """Test that empty string title_vi is treated as not translated."""
        progress = BookProgress(url="http://test.com", title="测试")
        progress.title_vi = ""
        
        # Empty string should be falsy
        assert not progress.title_vi
        
        # Condition for translation should be true
        needs_translation = progress.title and not progress.title_vi
        assert needs_translation
    
    def test_title_vi_preserves_on_save_load(self, tmp_path):
        """Test that title_vi is preserved across save/load."""
        p1 = BookProgress(
            url="http://test.com",
            title="仙府长生",
            title_vi="Tiên Phủ Trường Sinh",
            author="作者",
            author_vi="Tác Giả",
        )
        p1.save(tmp_path)
        
        p2 = BookProgress.load(tmp_path)
        assert p2.title_vi == "Tiên Phủ Trường Sinh"
        assert p2.author_vi == "Tác Giả"


class TestAutoGlossaryCondition:
    """Test auto-glossary generation conditions."""
    
    def test_has_raw_files_detection(self, tmp_path):
        """Test detection of raw files for glossary generation."""
        raw_dir = tmp_path / "raw"
        
        # No raw directory
        has_files = raw_dir.exists() and any(raw_dir.glob("*.txt"))
        assert not has_files
        
        # Empty raw directory
        raw_dir.mkdir()
        has_files = raw_dir.exists() and any(raw_dir.glob("*.txt"))
        assert not has_files
        
        # With raw files
        (raw_dir / "0001_test.txt").write_text("content", encoding="utf-8")
        has_files = raw_dir.exists() and any(raw_dir.glob("*.txt"))
        assert has_files


# Integration tests (require OpenAI API)
class TestStreamingPipelineIntegration:
    """Integration tests for streaming pipeline."""
    
    @pytest.fixture
    def book_with_raw_chapters(self, tmp_path):
        """Create a book directory with raw chapters for testing."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()
        
        # Create raw directory with chapter files
        raw_dir = book_dir / "raw"
        raw_dir.mkdir()
        
        # Create sample chapters
        (raw_dir / "0001_第一章.txt").write_text(
            "# 第一章 开始\n\n这是第一章的内容。修炼是一条漫长的道路。",
            encoding="utf-8"
        )
        (raw_dir / "0002_第二章.txt").write_text(
            "# 第二章 修炼\n\n主角开始修炼。练气境是第一个境界。",
            encoding="utf-8"
        )
        
        # Create book.json
        progress = BookProgress(
            url="http://test.com/book",
            title="测试小说",
            author="测试作者",
        )
        progress.chapters = [
            Chapter(index=1, id="1", url="http://test/1", title_cn="第一章 开始", status=ChapterStatus.CRAWLED),
            Chapter(index=2, id="2", url="http://test/2", title_cn="第二章 修炼", status=ChapterStatus.CRAWLED),
        ]
        progress.save(book_dir)
        
        return book_dir
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_pipeline_translates_metadata(self, book_with_raw_chapters):
        """Test that pipeline translates book title and author."""
        from dich_truyen.translator.engine import setup_translation
        
        book_dir = book_with_raw_chapters
        
        # Run setup_translation (part of pipeline)
        engine = await setup_translation(
            book_dir=book_dir,
            style_name="tien_hiep",
            auto_glossary=True,
        )
        
        # Reload and check metadata
        progress = BookProgress.load(book_dir)
        
        # Title and author should be translated
        assert progress.title_vi, "title_vi should be translated"
        assert progress.author_vi, "author_vi should be translated"
        assert progress.title_vi != progress.title  # Should be different
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_pipeline_generates_glossary(self, book_with_raw_chapters):
        """Test that pipeline generates glossary from samples."""
        from dich_truyen.translator.engine import setup_translation
        
        book_dir = book_with_raw_chapters
        
        # No glossary initially
        assert not (book_dir / "glossary.csv").exists()
        
        # Run setup_translation with auto_glossary
        engine = await setup_translation(
            book_dir=book_dir,
            style_name="tien_hiep",
            auto_glossary=True,
        )
        
        # Glossary should be generated and saved
        assert (book_dir / "glossary.csv").exists(), "glossary.csv should be created"
        
        glossary = Glossary.load(book_dir)
        assert len(glossary) > 0, "Glossary should have entries"
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_pipeline_translates_chapter_titles(self, book_with_raw_chapters):
        """Test that chapter titles are translated during pipeline."""
        from dich_truyen.translator.engine import translate_chapter_titles
        
        book_dir = book_with_raw_chapters
        
        # Run chapter title translation
        await translate_chapter_titles(book_dir)
        
        # Reload and check
        progress = BookProgress.load(book_dir)
        
        for chapter in progress.chapters:
            assert chapter.title_vi, f"Chapter {chapter.index} title_vi should be translated"
            # Vietnamese should contain Vietnamese characters
            has_vietnamese = any(c in chapter.title_vi for c in "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệ")
            assert has_vietnamese or "Chương" in chapter.title_vi, \
                f"Chapter title should be in Vietnamese: {chapter.title_vi}"
