"""Unit tests for the exporter module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from dich_truyen.exporter.calibre import CalibreExporter, ExportResult, export_book
from dich_truyen.formatter.metadata import BookMetadataManager
from dich_truyen.utils.progress import BookProgress, Chapter, ChapterStatus
from dich_truyen.config import CalibreConfig


class TestCalibreExporter:
    """Test CalibreExporter class."""

    @pytest.fixture
    def exporter(self):
        """Create test exporter."""
        return CalibreExporter(CalibreConfig(path="ebook-convert"))

    def test_supported_formats(self, exporter):
        """Test supported formats list."""
        assert "epub" in CalibreExporter.SUPPORTED_FORMATS
        assert "azw3" in CalibreExporter.SUPPORTED_FORMATS
        assert "mobi" in CalibreExporter.SUPPORTED_FORMATS
        assert "pdf" in CalibreExporter.SUPPORTED_FORMATS

    def test_unsupported_format_error(self, exporter, tmp_path):
        """Test error for unsupported format."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html></html>")

        result = exporter.export(html_file, "unsupported_format")
        assert not result.success
        assert "Unsupported format" in result.error_message

    def test_input_file_not_found(self, exporter, tmp_path):
        """Test error when input file not found."""
        result = exporter.export(tmp_path / "nonexistent.html", "epub")
        assert not result.success
        assert "not found" in result.error_message

    def test_build_command_basic(self, exporter):
        """Test building basic command."""
        with patch.object(exporter, '_find_calibre', return_value='/path/to/ebook-convert'):
            exporter._calibre_path = '/path/to/ebook-convert'
            
            cmd = exporter._build_command(
                input_path=Path("/input/book.html"),
                output_path=Path("/output/book.epub"),
            )
            
            assert cmd[0] == '/path/to/ebook-convert'
            # Use Path for cross-platform comparison
            assert "book.html" in cmd[1]
            assert "book.epub" in cmd[2]

    def test_build_command_with_metadata(self, exporter):
        """Test building command with metadata."""
        with patch.object(exporter, '_find_calibre', return_value='/path/to/ebook-convert'):
            exporter._calibre_path = '/path/to/ebook-convert'
            
            metadata = BookMetadataManager(
                title="Test Book",
                author="Test Author",
            )
            
            cmd = exporter._build_command(
                input_path=Path("/input/book.html"),
                output_path=Path("/output/book.epub"),
                metadata=metadata,
            )
            
            assert "--title" in cmd
            assert "Test Book" in cmd
            assert "--authors" in cmd
            assert "Test Author" in cmd


class TestExportResult:
    """Test ExportResult model."""

    def test_success_result(self):
        """Test successful export result."""
        result = ExportResult(success=True, output_path="/path/to/book.epub")
        assert result.success
        assert result.output_path == "/path/to/book.epub"
        assert result.error_message is None

    def test_failure_result(self):
        """Test failed export result."""
        result = ExportResult(success=False, error_message="Something went wrong")
        assert not result.success
        assert result.output_path is None
        assert result.error_message == "Something went wrong"


class TestExportBook:
    """Test export_book function."""

    @pytest.fixture
    def book_dir(self, tmp_path):
        """Create test book directory structure."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()

        # Create directories
        (book_dir / "formatted").mkdir()
        (book_dir / "output").mkdir()

        # Create book.json
        progress = BookProgress(
            url="http://example.com",
            title="剑来",
            title_vi="Kiếm Lai",
            author="烽火戏诸侯",
            chapters=[],
        )
        progress.save(book_dir)

        # Create formatted HTML
        (book_dir / "formatted" / "book.html").write_text(
            """<!DOCTYPE html>
<html lang="vi">
<head><title>Kiếm Lai</title></head>
<body>
<h1>Kiếm Lai</h1>
<h2 class="chapter-title">Chương 1</h2>
<p>Nội dung chương 1.</p>
</body>
</html>""",
            encoding="utf-8",
        )

        return book_dir

    def test_html_not_found(self, tmp_path):
        """Test error when HTML not found."""
        book_dir = tmp_path / "empty-book"
        book_dir.mkdir()
        (book_dir / "formatted").mkdir()

        result = export_book(book_dir, "epub")
        assert not result.success
        assert "not found" in result.error_message

    @patch('dich_truyen.exporter.calibre.CalibreExporter.export')
    def test_export_with_metadata(self, mock_export, book_dir):
        """Test export uses metadata from book progress."""
        mock_export.return_value = ExportResult(
            success=True, output_path=str(book_dir / "output/book.epub")
        )

        result = export_book(book_dir, "epub")

        # Verify export was called with metadata
        mock_export.assert_called_once()
        call_args = mock_export.call_args
        assert call_args.kwargs['metadata'] is not None
        assert call_args.kwargs['metadata'].title == "Kiếm Lai"


class TestCalibeFinding:
    """Test Calibre path finding."""

    def test_find_calibre_from_config(self, tmp_path):
        """Test finding Calibre from config path."""
        # Create a fake ebook-convert
        fake_calibre = tmp_path / "ebook-convert.exe"
        fake_calibre.write_text("fake")

        config = CalibreConfig(path=str(fake_calibre))
        exporter = CalibreExporter(config)

        path = exporter._find_calibre()
        assert path == str(fake_calibre)

    @patch('shutil.which')
    def test_find_calibre_in_path(self, mock_which):
        """Test finding Calibre in system PATH."""
        mock_which.return_value = "/usr/bin/ebook-convert"

        exporter = CalibreExporter()
        path = exporter._find_calibre()

        assert path == "/usr/bin/ebook-convert"

    @patch('shutil.which')
    @patch('pathlib.Path.exists')
    def test_calibre_not_found(self, mock_exists, mock_which):
        """Test error when Calibre not found."""
        mock_which.return_value = None
        mock_exists.return_value = False  # No common paths exist

        exporter = CalibreExporter(CalibreConfig(path="ebook-convert"))

        with pytest.raises(FileNotFoundError, match="ebook-convert not found"):
            exporter._find_calibre()


# Integration test (requires Calibre installed)
class TestExportIntegration:
    """Integration tests for export (require Calibre)."""

    @pytest.mark.skip(reason="Requires Calibre installed")
    def test_export_to_epub(self, tmp_path):
        """Test actual export to EPUB."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()
        (book_dir / "formatted").mkdir()
        (book_dir / "output").mkdir()

        # Create test HTML
        (book_dir / "formatted" / "book.html").write_text(
            """<!DOCTYPE html>
<html><head><title>Test</title></head>
<body><h1>Test Book</h1><p>Content</p></body>
</html>""",
            encoding="utf-8",
        )

        # Create book.json
        progress = BookProgress(url="http://example.com", title="Test")
        progress.save(book_dir)

        result = export_book(book_dir, "epub")
        assert result.success
        assert (book_dir / "output" / "book.epub").exists()
