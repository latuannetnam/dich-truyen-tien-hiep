# Improve Chapter Title Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve chapter title translation formatting in concurrent orchestrator mode to enforce strict `Chương [N] [Cleaned Title]` standards in both `book.json` and generated translated files.

**Architecture:** Integrate a robust Python verification and normalization guard inside `scripts/update_book_metadata.py` that parses `title_cn`, cleans any LLM-induced punctuation/spacing anomalies from `title_vi`, and updates `.agents/skills/translate-error-chapters/SKILL.md` to feed `title_cn` to the sub-agent and enforce correct top-line file formatting.

**Tech Stack:** Python 3.11, Pytest, `update_book_metadata.py` utility, `translate-error-chapters` agent skill.

---

### Task 1: Centralized Verification Guard & Test Suite

**Files:**
- Create: `tests/test_update_book_metadata.py`
- Modify: `scripts/update_book_metadata.py`

- [ ] **Step 1: Write the failing tests**
  Create a new test file `tests/test_update_book_metadata.py` containing comprehensive test scenarios for title normalization.
  
  ```python
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
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `uv run pytest tests/test_update_book_metadata.py -v`
  Expected: FAIL with `TypeError: update_metadata() takes 3 positional arguments but 4 were given`

- [ ] **Step 3: Implement guard and normalize title**
  Modify `scripts/update_book_metadata.py` signature to accept `title_cn: Optional[str] = None` and add the normalization guard logic.
  
  ```python
  # Add this to the imports in scripts/update_book_metadata.py:
  import re
  from typing import Optional

  # Update function signature:
  def update_metadata(book_dir: str, chapter_index: int, title_vi: str, title_cn: Optional[str] = None) -> None:
      ...
      chapter = chapters[chapter_index]

      # Run normalization guard
      if title_cn:
          ch_num_match = re.search(r'第\s*(\d+)\s*章', title_cn)
          if ch_num_match:
              num = ch_num_match.group(1)
              # Strip any "Chương <num>" prefix and colons/hyphens/dashes/spaces
              cleaned = re.sub(rf'^Chương\s*{num}\s*[:–-]*\s*', '', title_vi, flags=re.IGNORECASE)
              cleaned = re.sub(r'^[:–-\s]+', '', cleaned).strip()
              # Normalize multiple inner spaces
              cleaned = re.sub(r'\s+', ' ', cleaned)
              title_vi = f"Chương {num} {cleaned}"
      ...
  ```
  Also update the `__main__` entry point to parse the optional 4th argument:
  ```python
      title_vi_arg = sys.argv[3]
      title_cn_arg = sys.argv[4] if len(sys.argv) > 4 else None
      update_metadata(book_dir_arg, chapter_index_arg, title_vi_arg, title_cn_arg)
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `uv run pytest tests/test_update_book_metadata.py -v`
  Expected: PASS

- [ ] **Step 5: Run full project test suite**
  Run: `uv run pytest`
  Expected: PASS

- [ ] **Step 6: Commit**
  Run:
  ```bash
  git add scripts/update_book_metadata.py tests/test_update_book_metadata.py
  git commit -m "feat: add programmatic title normalization guard to update_metadata"
  ```

---

### Task 2: Sub-Agent Skill Upgrade

**Files:**
- Modify: `.agents/skills/translate-error-chapters/SKILL.md`

- [ ] **Step 1: Update Step 1 scanning to include title_cn in documentation**
  Modify `.agents/skills/translate-error-chapters/SKILL.md:27-33` to emphasize storing the `title_cn` alongside sequential index in the coordination queue:
  ```markdown
  * **Pending:** Chapters waiting to be translated, tracking sequential index, id, and raw `title_cn` from `book.json`.
  ```

- [ ] **Step 2: Update Sub-Agent execution protocol prompt template**
  Modify `.agents/skills/translate-error-chapters/SKILL.md:96-144` to add `title_cn` as an input and details about title translation and output format.
  
  *Context & Inputs additions:*
  ```markdown
  5. **Chinese Chapter Title:** The original Chinese title for this chapter is `[Chinese Chapter Title]` (from `book.json`).
  ```
  
  *Your Task Instructions additions:*
  ```markdown
  3. **Translate Chapter Title & Content:**
     * **Title Translation Rule:** Translate the provided Chinese Chapter Title (`[Chinese Chapter Title]`) into a clean Vietnamese chapter title `title_vi` according to these strict rules:
       1. Convert the chapter number prefix: `第[N]章` must be translated to `Chương [N]`.
       2. Translate the remaining Chinese characters of the chapter title into natural, capitalized Sino-Vietnamese (Hán-Việt) or Vietnamese meaning (matching Tiên Hiệp/Xianxia style guidelines). Capitalize the first letter of every word (Title Case) (e.g. `天魔传说` -> `Thiên Ma Truyền Thuyết`).
       3. Combine the number prefix and translated title with a single space as a separator: `Chương [N] [Translated Title]` (e.g., `Chương 1715 Thiên Ma Truyền Thuyết`). Do NOT use colons (`:`), hyphens/dashes (`-` or `–`), or extra brackets around the chapter number.
       4. Set the `title_vi` field in your JSON output to this exact value.
     * **Translate Content:** Translate the entire Chinese source text into natural, high-quality Vietnamese prose.
       * Apply all genre guidelines and vocabulary rules from the style guidelines and glossary.
       * Maintain consistent name/pronoun styles matching the previous chapter context.
  ```

  *Write Target File additions:*
  ```markdown
  5. **Write Target File:** Write the complete translated Vietnamese text directly to `[Absolute Path to books/<book-dir>/translating/<index>.txt]` using the `write_to_file` tool (with `Overwrite` set to true if replacing).
     * **Title Formatting in Content Rule:** The very first line of this file must contain the translated chapter title, formatted exactly as `# [title_vi]` (where `[title_vi]` is the translated chapter title, e.g., `# Chương 1715 Thiên Ma Truyền Thuyết`).
     * Ensure there is a blank line immediately after the first line.
  ```

- [ ] **Step 3: Update Concurrency Loop Step 3 instructions**
  Modify `.agents/skills/translate-error-chapters/SKILL.md:65-77` to include `title_cn` in `update_book_metadata.py`:
  ```markdown
  ```bash
  uv run python scripts/update_book_metadata.py "books/<book-dir>" <index_minus_1> "<title_vi>" "<title_cn>"
  ```
  ```

- [ ] **Step 4: Self-Review of SKILL.md changes**
  Read `.agents/skills/translate-error-chapters/SKILL.md` to ensure instructions flow naturally, are fully complete, and contain no TBDs/placeholders.

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add .agents/skills/translate-error-chapters/SKILL.md
  git commit -m "docs: improve translate-error-chapters skill with metadata title rules and programmatic guard"
  ```
