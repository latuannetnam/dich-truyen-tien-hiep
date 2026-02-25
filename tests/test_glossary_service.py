"""Tests for GlossaryService."""

import csv
from pathlib import Path

import pytest

from dich_truyen.services.glossary_service import GlossaryService


@pytest.fixture
def service_with_glossary(tmp_path: Path) -> tuple[GlossaryService, Path]:
    """Create a GlossaryService with a sample book + glossary."""
    book_dir = tmp_path / "test-book"
    book_dir.mkdir()

    glossary_path = book_dir / "glossary.csv"
    with open(glossary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["chinese", "vietnamese", "category", "notes"])
        writer.writerow(["王林", "Vương Lâm", "character", "Main character"])
        writer.writerow(["练气", "Luyện Khí", "realm", ""])

    return GlossaryService(books_dir=tmp_path), book_dir


class TestGlossaryService:
    """Tests for GlossaryService operations."""

    def test_get_glossary(self, service_with_glossary):
        svc, _ = service_with_glossary
        result = svc.get_glossary("test-book")
        assert result["total"] == 2
        assert result["entries"][0]["chinese"] == "王林"
        assert isinstance(result["categories"], list)

    def test_get_glossary_book_not_found(self, tmp_path):
        svc = GlossaryService(books_dir=tmp_path)
        with pytest.raises(ValueError, match="Book not found"):
            svc.get_glossary("nonexistent")

    def test_add_entry(self, service_with_glossary):
        svc, _ = service_with_glossary
        svc.add_entry("test-book", "筑基", "Trúc Cơ", "realm")
        result = svc.get_glossary("test-book")
        assert result["total"] == 3

    def test_remove_entry(self, service_with_glossary):
        svc, _ = service_with_glossary
        removed = svc.remove_entry("test-book", "王林")
        assert removed is True
        result = svc.get_glossary("test-book")
        assert result["total"] == 1

    def test_remove_nonexistent_entry(self, service_with_glossary):
        svc, _ = service_with_glossary
        removed = svc.remove_entry("test-book", "不存在")
        assert removed is False

    def test_export_csv(self, service_with_glossary):
        svc, _ = service_with_glossary
        csv_text = svc.export_csv("test-book")
        assert "王林" in csv_text
        assert "Vương Lâm" in csv_text
        lines = csv_text.strip().split("\n")
        assert len(lines) == 3  # header + 2 entries

    def test_import_csv(self, service_with_glossary):
        svc, _ = service_with_glossary
        csv_text = "chinese,vietnamese,category,notes\n筑基,Trúc Cơ,realm,\n金丹,Kim Đan,realm,"
        imported = svc.import_csv("test-book", csv_text)
        assert imported == 2
        result = svc.get_glossary("test-book")
        assert result["total"] == 4

    def test_get_empty_glossary(self, tmp_path):
        book_dir = tmp_path / "empty-book"
        book_dir.mkdir()
        svc = GlossaryService(books_dir=tmp_path)
        result = svc.get_glossary("empty-book")
        assert result["total"] == 0
        assert result["entries"] == []
