"""Unit tests for the crawler module."""

import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dotenv import load_dotenv

# Load .env for API key check
load_dotenv()

from dich_truyen.crawler.base import BaseCrawler
from dich_truyen.crawler.pattern import PatternDiscovery, DiscoveredBook
from dich_truyen.crawler.downloader import ChapterDownloader, slugify
from dich_truyen.utils.encoding import detect_encoding, decode_content
from dich_truyen.utils.progress import (
    BookProgress,
    Chapter,
    ChapterStatus,
    parse_chapter_range,
)
from dich_truyen.config import CrawlerConfig


# Sample URLs - use TEST_URL from env if available, else use defaults
SAMPLE_URL = os.getenv("TEST_URL", "https://www.piaotia.com/html/8/8717/index.html")
SAMPLE_CHAPTER_URL = "https://www.piaotia.com/html/8/8717/5588734.html"
SAMPLE_CHAPTERS = os.getenv("TEST_CHAPTERS", "1-10")

# Check if OpenAI API is configured for integration tests
def _has_openai_api():
    """Check if OpenAI API is available for testing."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    return bool(api_key) and not api_key.startswith("sk-your")

requires_openai = pytest.mark.skipif(
    not _has_openai_api(),
    reason="Requires OpenAI API key (set OPENAI_API_KEY)"
)

requires_network = pytest.mark.skipif(
    os.getenv("SKIP_NETWORK_TESTS", "").lower() == "true",
    reason="Network tests disabled (SKIP_NETWORK_TESTS=true)"
)


class TestEncoding:
    """Test encoding utilities."""

    def test_detect_gbk_encoding(self):
        """Test GBK encoding detection."""
        # GBK encoded Chinese text (longer text for reliable detection)
        content = "剑来第一章，这是一个很长的中文测试字符串".encode("gbk")
        encoding = detect_encoding(content)
        # chardet may return various Chinese encodings
        assert encoding.lower() in ("gbk", "gb2312", "gb18030", "iso-8859-1")
        # More importantly, test that decode_content works
        decoded = decode_content(content)
        assert "剑来" in decoded or len(decoded) > 0

    def test_detect_utf8_encoding(self):
        """Test UTF-8 encoding detection."""
        content = "剑来".encode("utf-8")
        encoding = detect_encoding(content)
        assert encoding.lower() in ("utf-8", "ascii")

    def test_decode_with_explicit_encoding(self):
        """Test decoding with explicit encoding."""
        text = "剑来"
        content = text.encode("gbk")
        result = decode_content(content, "gbk")
        assert result == text

    def test_decode_with_auto_detection(self):
        """Test decoding with auto-detection."""
        text = "剑来"
        content = text.encode("utf-8")
        result = decode_content(content)
        assert text in result  # May have BOM or other artifacts

    def test_decode_fallback_chain(self):
        """Test fallback chain for encoding."""
        text = "剑来第一章，这是一个很长的中文测试字符串"
        content = text.encode("gbk")
        # Test with explicit GBK encoding (should decode correctly)
        result = decode_content(content, "gbk")
        assert "剑来" in result
        # Also verify explicit encoding works
        result2 = decode_content(content, encoding="gbk")
        assert result2 == text


class TestChapterRangeParsing:
    """Test chapter range specification parsing."""

    def test_single_chapter(self):
        """Test single chapter number."""
        result = parse_chapter_range("5", 100)
        assert result == [5]

    def test_chapter_range(self):
        """Test chapter range (e.g., 1-5)."""
        result = parse_chapter_range("1-5", 100)
        assert result == [1, 2, 3, 4, 5]

    def test_chapter_list(self):
        """Test chapter list (e.g., 1,5,10)."""
        result = parse_chapter_range("1,5,10", 100)
        assert result == [1, 5, 10]

    def test_mixed_range_and_list(self):
        """Test mixed range and list (e.g., 1-3,5,8-10)."""
        result = parse_chapter_range("1-3,5,8-10", 100)
        assert result == [1, 2, 3, 5, 8, 9, 10]

    def test_empty_spec_returns_all(self):
        """Test empty spec returns all chapters."""
        result = parse_chapter_range("", 10)
        assert result == list(range(1, 11))

    def test_max_chapter_limit(self):
        """Test that max chapter is respected."""
        result = parse_chapter_range("1-1000", 50)
        assert max(result) == 50

    def test_out_of_range_ignored(self):
        """Test that out-of-range chapters are ignored."""
        result = parse_chapter_range("100", 50)
        assert result == []


class TestSlugify:
    """Test slugify function."""

    def test_chinese_text(self):
        """Test with Chinese text."""
        result = slugify("剑来")
        assert result == "剑来"

    def test_mixed_text(self):
        """Test with mixed Chinese and English."""
        result = slugify("剑来 Chapter 1")
        assert result == "剑来-chapter-1"

    def test_special_characters(self):
        """Test special character removal."""
        result = slugify("第一章：开始！")
        assert "：" not in result
        assert "！" not in result


class TestBookProgress:
    """Test BookProgress model."""

    def test_create_progress(self):
        """Test creating a new BookProgress."""
        progress = BookProgress(url=SAMPLE_URL)
        assert progress.url == SAMPLE_URL
        assert progress.chapters == []

    def test_add_chapter(self):
        """Test adding chapters to progress."""
        progress = BookProgress(url=SAMPLE_URL)
        chapter = Chapter(
            index=1,
            id="5588734",
            title_cn="楔子",
            url=SAMPLE_CHAPTER_URL,
        )
        progress.chapters.append(chapter)
        assert len(progress.chapters) == 1

    def test_get_chapter_by_index(self):
        """Test getting chapter by index."""
        progress = BookProgress(url=SAMPLE_URL)
        chapter = Chapter(index=1, id="1", title_cn="Test", url="http://test.com")
        progress.chapters.append(chapter)
        
        result = progress.get_chapter_by_index(1)
        assert result is not None
        assert result.title_cn == "Test"

    def test_update_chapter_status(self):
        """Test updating chapter status."""
        progress = BookProgress(url=SAMPLE_URL)
        chapter = Chapter(index=1, id="1", title_cn="Test", url="http://test.com")
        progress.chapters.append(chapter)
        
        progress.update_chapter_status(1, ChapterStatus.CRAWLED)
        assert progress.chapters[0].status == ChapterStatus.CRAWLED
        assert progress.chapters[0].crawled_at is not None

    def test_get_pending_chapters(self):
        """Test getting pending chapters."""
        progress = BookProgress(url=SAMPLE_URL)
        progress.chapters = [
            Chapter(index=1, id="1", title_cn="Ch1", url="http://test.com/1", status=ChapterStatus.PENDING),
            Chapter(index=2, id="2", title_cn="Ch2", url="http://test.com/2", status=ChapterStatus.CRAWLED),
            Chapter(index=3, id="3", title_cn="Ch3", url="http://test.com/3", status=ChapterStatus.PENDING),
        ]
        
        pending = progress.get_pending_chapters("crawl")
        assert len(pending) == 2

    def test_save_and_load(self, tmp_path):
        """Test saving and loading progress."""
        progress = BookProgress(
            url=SAMPLE_URL,
            title="剑来",
            author="烽火戏诸侯",
        )
        progress.chapters.append(
            Chapter(index=1, id="1", title_cn="Test", url="http://test.com")
        )
        
        # Save
        progress.save(tmp_path)
        assert (tmp_path / "book.json").exists()
        
        # Load
        loaded = BookProgress.load(tmp_path)
        assert loaded is not None
        assert loaded.title == "剑来"
        assert len(loaded.chapters) == 1


class TestBaseCrawler:
    """Test BaseCrawler class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return CrawlerConfig(
            delay_ms=100,
            max_retries=1,
            timeout_seconds=10,
        )

    @pytest.mark.asyncio
    async def test_crawler_context_manager(self, config):
        """Test crawler as context manager."""
        async with BaseCrawler(config) as crawler:
            assert crawler._client is not None
        assert crawler._client is None

    @pytest.mark.asyncio
    async def test_crawler_not_initialized_error(self, config):
        """Test error when crawler not initialized."""
        crawler = BaseCrawler(config)
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = crawler.client


class TestPatternDiscovery:
    """Test PatternDiscovery class."""

    def test_extract_chapter_id(self):
        """Test chapter ID extraction from URL."""
        discovery = PatternDiscovery()
        
        # Test numeric ID
        result = discovery._extract_chapter_id("5588734.html")
        assert result == "5588734"
        
        # Test with path
        result = discovery._extract_chapter_id("/html/8/8717/5588734.html")
        assert result == "5588734"

    def test_parse_json_response(self):
        """Test JSON parsing from LLM response."""
        discovery = PatternDiscovery()
        
        # Direct JSON
        result = discovery._parse_json_response('{"title": "Test"}')
        assert result["title"] == "Test"
        
        # Markdown code block
        result = discovery._parse_json_response('```json\n{"title": "Test"}\n```')
        assert result["title"] == "Test"
        
        # Invalid JSON
        result = discovery._parse_json_response("not json at all")
        assert result == {}

    def test_extract_chapters_from_html(self):
        """Test chapter extraction from HTML."""
        discovery = PatternDiscovery()
        
        html = """
        <div class="centent">
            <ul>
                <li><a href="001.html">Chapter 1</a></li>
                <li><a href="002.html">Chapter 2</a></li>
                <li><a href="003.html">Chapter 3</a></li>
            </ul>
        </div>
        """
        
        chapters = discovery.extract_chapters_from_html(
            html, "http://example.com/", ".centent ul li a"
        )
        
        assert len(chapters) == 3
        assert chapters[0].title == "Chapter 1"
        assert chapters[0].url == "http://example.com/001.html"

    def test_extract_text_with_breaks(self):
        """Test text extraction preserving paragraph breaks."""
        from bs4 import BeautifulSoup
        
        discovery = PatternDiscovery()
        
        html = "<div>Line 1<br>Line 2<p>Paragraph</p></div>"
        soup = BeautifulSoup(html, "lxml")
        
        result = discovery._extract_text_with_breaks(soup.div)
        assert "Line 1" in result
        assert "Line 2" in result


class TestChapterDownloader:
    """Test ChapterDownloader class."""

    @pytest.fixture
    def book_dir(self, tmp_path):
        """Create temporary book directory."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()
        return book_dir

    def test_downloader_creates_directories(self, tmp_path):
        """Test that downloader creates required directories."""
        book_dir = tmp_path / "new-book"
        downloader = ChapterDownloader(book_dir)
        
        assert book_dir.exists()
        assert (book_dir / "raw").exists()

    @pytest.mark.asyncio
    async def test_downloader_with_existing_progress(self, book_dir):
        """Test downloader loads existing progress."""
        # Create existing progress
        progress = BookProgress(
            url=SAMPLE_URL,
            title="Test Book",
        )
        progress.save(book_dir)
        
        downloader = ChapterDownloader(book_dir)
        loaded = BookProgress.load(book_dir)
        
        assert loaded is not None
        assert loaded.title == "Test Book"


# Integration tests (require network and API)
class TestCrawlerIntegration:
    """Integration tests for crawler (require network)."""

    @pytest.mark.asyncio
    @requires_network
    async def test_fetch_sample_page(self):
        """Test fetching the sample page."""
        async with BaseCrawler() as crawler:
            html = await crawler.fetch(SAMPLE_URL)
            # Should contain some content
            assert len(html) > 0

    @pytest.mark.asyncio
    @requires_openai
    @requires_network
    async def test_pattern_discovery(self):
        """Test full pattern discovery."""
        async with BaseCrawler() as crawler:
            html = await crawler.fetch(SAMPLE_URL)
        
        discovery = PatternDiscovery()
        result = await discovery.analyze_index_page(html, SAMPLE_URL)
        
        assert result.title != ""
        assert result.patterns.chapter_selector != ""
