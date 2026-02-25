"""Tests for BookService and StyleService.

ExportService requires actual book data and is tested via integration tests.
"""

import json
from pathlib import Path

import pytest

from dich_truyen.services.book_service import BookService
from dich_truyen.services.style_service import StyleService


# --- BookService ---


@pytest.fixture
def books_dir(tmp_path: Path) -> Path:
    """Create a temp books dir with one book."""
    book_dir = tmp_path / "test-book"
    book_dir.mkdir()
    (book_dir / "book.json").write_text(
        json.dumps({
            "url": "https://example.com/book",
            "title": "测试书",
            "title_vi": "Sách Test",
            "author": "作者",
            "author_vi": "Tác Giả",
            "encoding": "utf-8",
            "chapters": [
                {
                    "index": 1,
                    "id": "ch1",
                    "title_cn": "第一章",
                    "title_vi": "Chương 1",
                    "url": "https://example.com/ch1",
                    "status": "translated",
                },
                {
                    "index": 2,
                    "id": "ch2",
                    "title_cn": "第二章",
                    "url": "https://example.com/ch2",
                    "status": "crawled",
                },
            ],
        }),
        encoding="utf-8",
    )
    # Create chapter content
    translated_dir = book_dir / "translated"
    translated_dir.mkdir()
    (translated_dir / "chapter_0001.txt").write_text("Nội dung chương 1", encoding="utf-8")
    return tmp_path


def test_book_service_list(books_dir: Path) -> None:
    """List books returns summary."""
    service = BookService(books_dir)
    books = service.list_books()
    assert len(books) == 1
    assert books[0]["id"] == "test-book"
    assert books[0]["title"] == "测试书"
    assert books[0]["total_chapters"] == 2
    assert books[0]["translated_chapters"] == 1


def test_book_service_get(books_dir: Path) -> None:
    """Get book returns full details."""
    service = BookService(books_dir)
    book = service.get_book("test-book")
    assert book["title_vi"] == "Sách Test"
    assert len(book["chapters"]) == 2
    assert book["chapters"][0]["status"] == "translated"


def test_book_service_not_found(tmp_path: Path) -> None:
    """Get nonexistent book raises ValueError."""
    service = BookService(tmp_path)
    with pytest.raises(ValueError, match="Book not found"):
        service.get_book("nonexistent")


def test_book_service_chapter_content(books_dir: Path) -> None:
    """Read chapter content returns translated text."""
    service = BookService(books_dir)
    content = service.get_chapter_content("test-book", 1)
    assert content["translated"] == "Nội dung chương 1"
    assert content["raw"] == ""


# --- StyleService ---


def test_style_service_list() -> None:
    """List styles returns at least the built-in styles."""
    service = StyleService()
    styles = service.list_styles()
    assert len(styles) > 0
    # All should have name and is_builtin
    for s in styles:
        assert "name" in s
        assert "is_builtin" in s


def test_style_service_get_names() -> None:
    """Get style names returns a non-empty list."""
    service = StyleService()
    names = service.get_style_names()
    assert isinstance(names, list)
    assert len(names) > 0


def test_style_service_load() -> None:
    """Load a built-in style returns full template."""
    service = StyleService()
    names = service.get_style_names()
    style = service.get_style(names[0])
    assert "name" in style
    assert "guidelines" in style
    assert isinstance(style["guidelines"], list)
