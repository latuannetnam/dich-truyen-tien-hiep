import json

from scratch.fix_chapter_names import fix_chapter_names


def test_fix_chapter_names_dry_run(tmp_path):
    # Setup mock books/15112-indexhtml structure in tmp_path
    book_dir = tmp_path / "books" / "15112-indexhtml"
    translating_dir = book_dir / "translating"
    translating_dir.mkdir(parents=True)

    # Create book.json
    book_json_path = book_dir / "book.json"
    book_data = {
        "chapters": [{"index": 1622, "title_cn": "第1664章 灾难级", "title_vi": "Cấp Tai Họa"}]
    }
    with open(book_json_path, "w", encoding="utf-8") as f:
        json.dump(book_data, f)

    # Create chapter file
    chap_file = translating_dir / "1622.txt"
    original_content = "Chương 1622: Cấp Tai Họa\n\nContent line 1\nContent line 2\n"
    with open(chap_file, "w", encoding="utf-8") as f:
        f.write(original_content)

    # Run in dry-run mode
    fix_chapter_names(book_dir=book_dir, dry_run=True)

    # Verify no file content changed
    with open(chap_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == original_content


def test_fix_chapter_names_execute(tmp_path):
    # Setup mock books/15112-indexhtml structure in tmp_path
    book_dir = tmp_path / "books" / "15112-indexhtml"
    translating_dir = book_dir / "translating"
    translating_dir.mkdir(parents=True)

    # Create book.json
    book_json_path = book_dir / "book.json"
    book_data = {
        "chapters": [{"index": 1622, "title_cn": "第1664章 灾难级", "title_vi": "Cấp Tai Họa"}]
    }
    with open(book_json_path, "w", encoding="utf-8") as f:
        json.dump(book_data, f)

    # Create chapter file
    chap_file = translating_dir / "1622.txt"
    original_content = "Chương 1622: Cấp Tai Họa\n\nContent line 1\nContent line 2\n"
    with open(chap_file, "w", encoding="utf-8") as f:
        f.write(original_content)

    # Run in execute mode
    fix_chapter_names(book_dir=book_dir, dry_run=False)

    # Verify file content changed correctly
    with open(chap_file, "r", encoding="utf-8") as f:
        content = f.read()
    expected_content = "Chương 1664: Cấp Tai Họa\n\nContent line 1\nContent line 2\n"
    assert content == expected_content
