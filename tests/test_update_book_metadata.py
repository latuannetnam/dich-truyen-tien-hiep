import json
import pytest
from pathlib import Path
from scripts.update_book_metadata import update_metadata

def test_title_normalization_guard(tmp_path):
    # Create a mock book directory and book.json
    book_dir = tmp_path / "mock_book"
    book_dir.mkdir()
    book_json = book_dir / "book.json"
    
    mock_data = {
        "chapters": [
            {
                "index": 1,
                "id": "1001",
                "title_cn": "第1715章 天魔传说",
                "title_vi": None,
                "status": "crawled"
            }
        ]
    }
    
    with open(book_json, "w", encoding="utf-8") as f:
        json.dump(mock_data, f, indent=2)

    # Scenario A: Title has colons and extra spaces
    update_metadata(str(book_dir), 0, "Chương 1715:  Thiên Ma Truyền Thuyết  ", "第1715章 天魔传说")
    with open(book_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["chapters"][0]["title_vi"] == "Chương 1715 Thiên Ma Truyền Thuyết"

    # Scenario B: Title has hyphens/dashes
    update_metadata(str(book_dir), 0, "Chương 1715 – Thiên Ma Truyền Thuyết", "第1715章 天魔传说")
    with open(book_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["chapters"][0]["title_vi"] == "Chương 1715 Thiên Ma Truyền Thuyết"

    # Scenario C: Title is just semantic part
    update_metadata(str(book_dir), 0, "Thiên Ma Truyền Thuyết", "第1715章 天魔传说")
    with open(book_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["chapters"][0]["title_vi"] == "Chương 1715 Thiên Ma Truyền Thuyết"
