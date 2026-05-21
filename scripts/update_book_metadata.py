#!/usr/bin/env python3
"""Programmatic utility to update chapter metadata in book.json without fragile text find-and-replace."""

import json
import sys
from datetime import datetime
from pathlib import Path


def update_metadata(book_dir: str, chapter_index: int, title_vi: str) -> None:
    """Updates book.json metadata for a specific chapter.

    Args:
        book_dir: Path to the book directory (e.g. books/15112-indexhtml).
        chapter_index: 0-based index of the chapter to update.
        title_vi: The translated Vietnamese title for the chapter.
    """
    book_path = Path(book_dir) / "book.json"
    if not book_path.exists():
        print(f"Error: {book_path} does not exist.")
        sys.exit(1)

    try:
        with open(book_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading/parsing {book_path}: {e}")
        sys.exit(1)

    chapters = data.get("chapters", [])
    if chapter_index < 0 or chapter_index >= len(chapters):
        print(f"Error: Index {chapter_index} is out of range (total chapters: {len(chapters)}).")
        sys.exit(1)

    chapter = chapters[chapter_index]

    # Safety Check: Verify index alignment to catch off-by-one errors
    actual_seq_index = chapter.get("index")
    if actual_seq_index is not None and actual_seq_index != chapter_index + 1:
        print(
            f"Warning: Array index {chapter_index} targets a chapter with sequence 'index': {actual_seq_index} (expected {chapter_index + 1})."
        )

    # Track changes for reporting
    old_title_vi = chapter.get("title_vi")
    old_status = chapter.get("status")

    chapter["title_vi"] = title_vi
    chapter["status"] = "translated"
    chapter["translated_at"] = datetime.utcnow().isoformat().replace("+00:00", "") + "Z"
    chapter["error_message"] = None

    try:
        with open(book_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully updated Chapter {chapter_index + 1} ({chapter.get('id')}):")
        print(f"  - Title (VI): {old_title_vi} -> {title_vi}")
        print(f"  - Status: {old_status} -> translated")
        print("  - Error Message: -> null")
    except Exception as e:
        print(f"Error writing update to {book_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if len(sys.argv) < 4:
        print("Usage: python update_book_metadata.py <book_dir> <chapter_index> <title_vi>")
        sys.exit(1)

    book_dir_arg = sys.argv[1]
    try:
        chapter_index_arg = int(sys.argv[2])
    except ValueError:
        print(f"Error: Chapter index must be an integer, got '{sys.argv[2]}'.")
        sys.exit(1)

    title_vi_arg = sys.argv[3]
    update_metadata(book_dir_arg, chapter_index_arg, title_vi_arg)
