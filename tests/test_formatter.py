"""Unit tests for the formatter module."""

import pytest

from dich_truyen.formatter.assembler import HTMLAssembler
from dich_truyen.formatter.metadata import BookMetadataManager
from dich_truyen.utils.progress import BookProgress, Chapter, ChapterStatus


class TestBookMetadataManager:
    """Test BookMetadataManager class."""

    def test_create_metadata(self):
        """Test creating metadata."""
        metadata = BookMetadataManager(
            title="Kiếm Lai",
            title_original="剑来",
            author="Phong Hỏa Hí Chư Hầu",
            translator="AI Translator",
        )
        assert metadata.title == "Kiếm Lai"
        assert metadata.language == "vi"

    def test_from_book_progress(self):
        """Test creating from book progress."""
        progress = BookProgress(
            url="http://example.com",
            title="剑来",
            title_vi="Kiếm Lai",
            author="烽火戏诸侯",
        )

        metadata = BookMetadataManager.from_book_progress(progress)
        assert metadata.title == "Kiếm Lai"
        assert metadata.title_original == "剑来"

    def test_to_calibre_args(self):
        """Test generating Calibre arguments."""
        metadata = BookMetadataManager(
            title="Kiếm Lai",
            author="Phong Hỏa",
            description="A great novel",
        )

        args = metadata.to_calibre_args()
        assert "--title" in args
        assert "Kiếm Lai" in args
        assert "--authors" in args
        assert "--comments" in args

    def test_to_html_meta(self):
        """Test generating HTML meta tags."""
        metadata = BookMetadataManager(
            title="Kiếm Lai",
            author="Phong Hỏa",
            translator="AI",
        )

        html = metadata.to_html_meta()
        assert 'name="author"' in html
        assert 'name="translator"' in html
        assert "Phong Hỏa" in html

    def test_update_progress(self):
        """Test updating book progress."""
        progress = BookProgress(
            url="http://example.com",
            title="剑来",
        )

        metadata = BookMetadataManager(
            title="Kiếm Lai",
            author="Author",
            translator="Translator",
            description="Description",
        )

        metadata.update_progress(progress)
        assert progress.title_vi == "Kiếm Lai"
        assert progress.metadata.translator == "Translator"


class TestHTMLAssembler:
    """Test HTMLAssembler class."""

    @pytest.fixture
    def book_dir(self, tmp_path):
        """Create test book directory structure."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()

        # Create directories
        (book_dir / "raw").mkdir()
        (book_dir / "translated").mkdir()
        (book_dir / "formatted").mkdir()

        # Create book.json
        progress = BookProgress(
            url="http://example.com",
            title="剑来",
            title_vi="Kiếm Lai",
            author="烽火戏诸侯",
            chapters=[
                Chapter(
                    index=1,
                    id="001",
                    title_cn="楔子",
                    url="http://example.com/001",
                    status=ChapterStatus.TRANSLATED,
                ),
                Chapter(
                    index=2,
                    id="002",
                    title_cn="第一章",
                    url="http://example.com/002",
                    status=ChapterStatus.TRANSLATED,
                ),
            ],
        )
        progress.save(book_dir)

        # Create translated chapter files
        (book_dir / "translated" / "0001_gioi-thieu.txt").write_text(
            "# Giới thiệu\n\nĐây là đoạn đầu.\n\nĐây là đoạn thứ hai.",
            encoding="utf-8",
        )
        (book_dir / "translated" / "0002_chuong-mot.txt").write_text(
            "# Chương 1\n\nNội dung chương 1.\n\nĐoạn tiếp theo.",
            encoding="utf-8",
        )

        return book_dir

    def test_load_book_data(self, book_dir):
        """Test loading book data."""
        assembler = HTMLAssembler(book_dir)
        assembler.load_book_data()

        assert assembler.progress is not None
        assert assembler.metadata is not None
        assert assembler.metadata.title == "Kiếm Lai"

    def test_get_translated_chapters(self, book_dir):
        """Test getting translated chapters."""
        assembler = HTMLAssembler(book_dir)
        chapters = assembler.get_translated_chapters()

        assert len(chapters) == 2
        assert chapters[0][0].index == 1
        assert chapters[0][1].exists()

    def test_read_chapter_content(self, book_dir):
        """Test reading chapter content."""
        assembler = HTMLAssembler(book_dir)
        file_path = book_dir / "translated" / "0001_gioi-thieu.txt"

        content = assembler.read_chapter_content(file_path)
        assert "<p>" in content
        assert "Đây là đoạn đầu" in content

    def test_get_chapter_title(self, book_dir):
        """Test getting chapter title."""
        assembler = HTMLAssembler(book_dir)
        assembler.load_book_data()

        chapter = assembler.progress.chapters[0]
        file_path = book_dir / "translated" / "0001_gioi-thieu.txt"

        title = assembler.get_chapter_title(chapter, file_path)
        assert title == "Giới thiệu"

    def test_generate_toc(self, book_dir):
        """Test generating table of contents."""
        assembler = HTMLAssembler(book_dir)
        chapters = assembler.get_translated_chapters()
        toc = assembler.generate_toc(chapters)

        assert 'href="#chapter-1"' in toc
        assert 'href="#chapter-2"' in toc

    def test_format_chapter(self, book_dir):
        """Test formatting a single chapter."""
        assembler = HTMLAssembler(book_dir)
        assembler.load_book_data()

        chapter = assembler.progress.chapters[0]
        file_path = book_dir / "translated" / "0001_gioi-thieu.txt"

        html = assembler.format_chapter(chapter, file_path)
        assert 'id="chapter-1"' in html
        assert 'class="chapter-title"' in html

    def test_assemble(self, book_dir):
        """Test full book assembly."""
        assembler = HTMLAssembler(book_dir)
        output_path = assembler.assemble()

        assert output_path.exists()
        assert output_path.name == "book.html"

        content = output_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Kiếm Lai" in content
        assert "Mục Lục" in content
        assert 'id="chapter-1"' in content
        assert 'id="chapter-2"' in content

    def test_assemble_with_overrides(self, book_dir):
        """Test assembly with metadata overrides."""
        assembler = HTMLAssembler(book_dir)
        output_path = assembler.assemble(
            title="Custom Title",
            author="Custom Author",
            translator="Custom Translator",
        )

        content = output_path.read_text(encoding="utf-8")
        assert "Custom Title" in content
        assert "Custom Author" in content
        assert "Custom Translator" in content


class TestVietnameseTypography:
    """Test Vietnamese typography handling."""

    def test_diacritics_preserved(self, tmp_path):
        """Test that Vietnamese diacritics are preserved."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()
        (book_dir / "translated").mkdir()
        (book_dir / "formatted").mkdir()

        # Create progress
        progress = BookProgress(
            url="http://example.com",
            title="Kiếm Lai",
            author="Tác giả",
            chapters=[
                Chapter(
                    index=1,
                    id="1",
                    title_cn="Test",
                    url="http://example.com/1",
                    status=ChapterStatus.TRANSLATED,
                ),
            ],
        )
        progress.save(book_dir)

        # Create file with Vietnamese diacritics
        vietnamese_text = """# Chương 1: Kiếm Lai

Trần Bình An đứng trên ngọn núi, nhìn xa xăm về phía chân trời.

"Đạo hữu, ngươi đến từ đâu?" Một giọng nói vang lên từ phía sau.

Hắn quay lại, ánh mắt sắc bén như kiếm."""

        (book_dir / "translated" / "0001_test.txt").write_text(vietnamese_text, encoding="utf-8")

        # Assemble
        assembler = HTMLAssembler(book_dir)
        output_path = assembler.assemble()

        content = output_path.read_text(encoding="utf-8")

        # Check diacritics preserved
        assert "Trần Bình An" in content
        assert "ngọn núi" in content
        assert "Đạo hữu" in content
        assert "sắc bén" in content
