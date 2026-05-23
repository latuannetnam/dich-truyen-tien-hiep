# Fix Translating Chapter Names Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the 70 mismatched chapter files in `books/15112-indexhtml/translating/` by matching them against `book.json` and correcting their first lines to reflect the proper Chinese chapter number.

**Architecture:** We use a simple, robust Python CLI utility script in `scratch/fix_chapter_names.py` which loads `book.json`, maps file sequential index to `book.json` indices, parses the correct Chinese chapter number from `title_cn`, extracts the existing title suffix from the first line of the file, and replaces the first line in place with proper encoding, while preserving all other paragraphs and formatting.

**Tech Stack:** Python 3.11+, pathlib, re, json, pytest (for TDD).

---

### Task 1: Write Unit Tests (TDD Setup)

**Files:**
- Create: `tests/test_fix_chapter_names.py`

- [ ] **Step 1: Write the failing tests**
  Create `tests/test_fix_chapter_names.py` with mock directories and data to verify the correct behavior of the cleanup function under both dry-run and execution modes.

```python
import json
from pathlib import Path
import pytest
from scratch.fix_chapter_names import fix_chapter_names

def test_fix_chapter_names_dry_run(tmp_path):
    # Setup mock books/15112-indexhtml structure in tmp_path
    book_dir = tmp_path / "books" / "15112-indexhtml"
    translating_dir = book_dir / "translating"
    translating_dir.mkdir(parents=True)
    
    # Create book.json
    book_json_path = book_dir / "book.json"
    book_data = {
        "chapters": [
            {
                "index": 1622,
                "title_cn": "第1664章 灾难级",
                "title_vi": "Cấp Tai Họa"
            }
        ]
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
        "chapters": [
            {
                "index": 1622,
                "title_cn": "第1664章 灾难级",
                "title_vi": "Cấp Tai Họa"
            }
        ]
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
```

- [ ] **Step 2: Run tests to verify they fail**
  Run the test suite using pytest to ensure the tests fail due to missing modules/functions.
  Run: `uv run pytest tests/test_fix_chapter_names.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'scratch.fix_chapter_names'`

---

### Task 2: Implement the Fix Script

**Files:**
- Create: `scratch/fix_chapter_names.py`

- [ ] **Step 1: Write minimal implementation**
  Create `scratch/fix_chapter_names.py` and implement the correction logic to satisfy the test assertions.

```python
import argparse
import json
from pathlib import Path
import re

def fix_chapter_names(book_dir: Path, dry_run: bool = True) -> None:
    book_json_path = book_dir / "book.json"
    translating_dir = book_dir / "translating"

    if not book_json_path.exists():
        print(f"Error: {book_json_path} not found")
        return

    if not translating_dir.exists():
        print(f"Error: {translating_dir} not found")
        return

    with open(book_json_path, "r", encoding="utf-8") as f:
        book_data = json.load(f)

    chapters = {c["index"]: c for c in book_data.get("chapters", [])}
    txt_files = sorted(list(translating_dir.glob("*.txt")), key=lambda p: int(p.stem) if p.stem.isdigit() else 999999)

    mismatches_found = 0
    fixed_count = 0

    print(f"Scanning {translating_dir}... Total txt files: {len(txt_files)}")
    if dry_run:
        print("RUNNING IN DRY-RUN MODE (No files will be modified)")

    for file_path in txt_files:
        if not file_path.stem.isdigit():
            continue
        index = int(file_path.stem)
        chapter_data = chapters.get(index)
        if not chapter_data:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            continue

        first_line = lines[0].strip()
        cn_match = re.search(r"第(\d+)章", chapter_data.get("title_cn", ""))
        if not cn_match:
            continue

        cn_num = cn_match.group(1)
        fl_match = re.search(r"Chương\s+(\d+)", first_line)
        if not fl_match:
            continue

        fl_num = fl_match.group(1)
        if fl_num != cn_num:
            mismatches_found += 1
            
            # Extract title suffix
            title_part = ""
            if ":" in first_line:
                title_part = first_line.split(":", 1)[1].strip()
            elif " " in first_line:
                parts = first_line.split(" ", 2)
                title_part = parts[2].strip() if len(parts) > 2 else ""

            new_first_line = f"Chương {cn_num}: {title_part}" if title_part else f"Chương {cn_num}"
            
            # Preserve original newline of the first line
            orig_newline = "\n"
            if lines[0].endswith("\r\n"):
                orig_newline = "\r\n"
            
            new_first_line_with_newline = new_first_line + orig_newline

            print(f"File {file_path.name}:")
            print(f"  Current: '{first_line}'")
            print(f"  New:     '{new_first_line}'")

            if not dry_run:
                lines[0] = new_first_line_with_newline
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                fixed_count += 1

    print(f"\nScan completed.")
    print(f"Total mismatches found: {mismatches_found}")
    if dry_run:
        print(f"Dry-run finished. No files were changed. Run with --execute to commit changes.")
    else:
        print(f"Successfully fixed {fixed_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix chapter prefixes in translating folder")
    parser.add_argument("--execute", action="store_true", help="Commit the changes to files")
    parser.add_argument("--book-dir", type=str, default="books/15112-indexhtml", help="Path to book directory")
    args = parser.parse_args()

    fix_chapter_names(Path(args.book_dir), dry_run=not args.execute)
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `uv run pytest tests/test_fix_chapter_names.py -v`
  Expected: PASS

- [ ] **Step 3: Run linter and formatter**
  Run: `uv run ruff check scratch/fix_chapter_names.py tests/test_fix_chapter_names.py --fix`
  Run: `uv run ruff format scratch/fix_chapter_names.py tests/test_fix_chapter_names.py`
  Expected: Passes linting/formatting checks with no issues.

- [ ] **Step 4: Commit Code and Tests**
  Run:
  ```bash
  git add scratch/fix_chapter_names.py tests/test_fix_chapter_names.py
  git commit -m "feat: add utility script to fix translating chapter names with TDD tests"
  ```

---

### Task 3: Perform Dry-Run & Execution on Real Data

**Files:**
- None (Utility execution)

- [ ] **Step 1: Execute Dry-Run Scan on books/15112-indexhtml**
  Execute the script in dry-run mode (default) to log the planned chapter mappings.
  Run: `uv run python scratch/fix_chapter_names.py`
  Expected:
  - Logs showing planned replacements (e.g. `File 1622.txt: Current: 'Chương 1622: Cấp Tai Họa' New: 'Chương 1664: Cấp Tai Họa'`).
  - "Total mismatches found: 70".
  - No files are written to or modified.

- [ ] **Step 2: Execute Real Fix**
  Run the script with the `--execute` flag to commit the corrections to disk.
  Run: `uv run python scratch/fix_chapter_names.py --execute`
  Expected:
  - Logs showing execution writes.
  - "Successfully fixed 70 files."

---

### Task 4: Post-Fix Validation

**Files:**
- None (Validation run)

- [ ] **Step 1: Run mismatch scan script**
  Run the verification scanner `check_translating.py` to check the `translating/` folder again.
  Run: `uv run python scratch/check_translating.py`
  Expected:
  - Output log in `scratch/analysis_log.txt` lists:
    `Mismatches in translating: 0 out of 110`.

- [ ] **Step 2: Clean up scratch/check_translating.py & scratch/analysis_log.txt**
  Discard the checking scripts since validation is complete.
  Run:
  ```bash
  git checkout -- scratch/check_translating.py
  rm scratch/analysis_log.txt
  ```
