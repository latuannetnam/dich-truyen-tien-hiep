"""Progress tracking utilities for resumable operations."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ChapterStatus(str, Enum):
    """Chapter processing status."""

    PENDING = "pending"
    CRAWLED = "crawled"
    TRANSLATED = "translated"
    FORMATTED = "formatted"
    EXPORTED = "exported"
    ERROR = "error"


class Chapter(BaseModel):
    """Chapter metadata and status."""

    index: int = Field(description="Chapter index (1-based)")
    id: str = Field(description="Chapter ID from URL")
    title_cn: str = Field(default="", description="Original Chinese title")
    title_vi: Optional[str] = Field(default=None, description="Translated Vietnamese title")
    url: str = Field(description="Chapter URL")
    status: ChapterStatus = Field(default=ChapterStatus.PENDING)
    crawled_at: Optional[datetime] = None
    translated_at: Optional[datetime] = None
    error_message: Optional[str] = None


class BookPatterns(BaseModel):
    """Extracted patterns for crawling."""

    chapter_selector: str = Field(default="", description="CSS selector for chapter links")
    content_selector: str = Field(default="#content", description="CSS selector for content")
    title_selector: str = Field(default="h1", description="CSS selector for chapter title")
    elements_to_remove: list[str] = Field(
        default_factory=lambda: ["script", "style", ".toplink", "table"],
        description="Elements to remove from content",
    )


class BookMetadata(BaseModel):
    """Book metadata for formatting and export."""

    translator: str = Field(default="", description="Translator name")
    description: str = Field(default="", description="Book description/synopsis")
    cover_path: Optional[str] = Field(default=None, description="Path to cover image")


class BookProgress(BaseModel):
    """Book progress tracking."""

    url: str = Field(description="Book index URL")
    title: str = Field(default="", description="Original Chinese title")
    title_vi: str = Field(default="", description="Vietnamese title")
    author: str = Field(default="", description="Author name in Chinese")
    author_vi: str = Field(default="", description="Author name in Vietnamese")
    encoding: str = Field(default="utf-8", description="Content encoding")
    patterns: BookPatterns = Field(default_factory=BookPatterns)
    chapters: list[Chapter] = Field(default_factory=list)
    metadata: BookMetadata = Field(default_factory=BookMetadata)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_chapter_by_index(self, index: int) -> Optional[Chapter]:
        """Get chapter by 1-based index."""
        for chapter in self.chapters:
            if chapter.index == index:
                return chapter
        return None

    def get_chapters_by_status(self, status: ChapterStatus) -> list[Chapter]:
        """Get all chapters with the given status."""
        return [c for c in self.chapters if c.status == status]

    def get_pending_chapters(self, phase: str) -> list[Chapter]:
        """Get chapters pending for a specific phase."""
        if phase == "crawl":
            return [c for c in self.chapters if c.status == ChapterStatus.PENDING]
        elif phase == "translate":
            return [c for c in self.chapters if c.status == ChapterStatus.CRAWLED]
        elif phase == "format":
            return [c for c in self.chapters if c.status == ChapterStatus.TRANSLATED]
        return []

    def update_chapter_status(
        self,
        index: int,
        status: ChapterStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update a chapter's status."""
        chapter = self.get_chapter_by_index(index)
        if chapter:
            chapter.status = status
            chapter.error_message = error
            if status == ChapterStatus.CRAWLED:
                chapter.crawled_at = datetime.now()
            elif status == ChapterStatus.TRANSLATED:
                chapter.translated_at = datetime.now()
            self.updated_at = datetime.now()

    def save(self, book_dir: Path) -> None:
        """Save progress to book.json."""
        progress_file = book_dir / "book.json"
        self.updated_at = datetime.now()
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

    @classmethod
    def load(cls, book_dir: Path) -> Optional["BookProgress"]:
        """Load progress from book.json if it exists."""
        progress_file = book_dir / "book.json"
        if not progress_file.exists():
            return None
        with open(progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

    @classmethod
    def load_or_create(cls, book_dir: Path, url: str) -> "BookProgress":
        """Load existing progress or create new."""
        progress = cls.load(book_dir)
        if progress is None:
            progress = cls(url=url)
        return progress


def parse_chapter_range(spec: str, max_chapter: int) -> list[int]:
    """Parse chapter range specification.

    Args:
        spec: Range specification like "1-100" or "1,5,10-20"
        max_chapter: Maximum chapter number

    Returns:
        List of chapter indices (1-based)

    Examples:
        "1-10" -> [1, 2, 3, ..., 10]
        "1,5,10" -> [1, 5, 10]
        "1-5,10,15-20" -> [1, 2, 3, 4, 5, 10, 15, 16, 17, 18, 19, 20]
    """
    if not spec:
        return list(range(1, max_chapter + 1))

    result = set()
    parts = spec.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = int(start.strip())
            end = int(end.strip())
            result.update(range(start, min(end + 1, max_chapter + 1)))
        else:
            idx = int(part)
            if 1 <= idx <= max_chapter:
                result.add(idx)

    return sorted(result)
