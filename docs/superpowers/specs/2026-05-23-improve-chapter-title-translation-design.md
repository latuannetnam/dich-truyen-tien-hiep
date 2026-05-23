# Design Doc: Improve Chapter Title Translation in Concurrent Orchestrator Mode

- **Date:** 2026-05-23
- **Author:** Antigravity
- **Status:** Approved

## Goal Description

Improve the chapter translation orchestrator skill (`.agents/skills/translate-error-chapters/SKILL.md`) to correctly set translated chapter names based on the original metadata in `book.json`. 

Specifically, for chapters with a Chinese title like `第1715章 天魔传说`, the translated title `title_vi` in `book.json` and the chapter name/first line in the translated content (e.g. `books/<book-dir>/translating/<index>.txt`) must both strictly match:
`Chương 1715 Thiên Ma Truyền Thuyết` (and `# Chương 1715 Thiên Ma Truyền Thuyết` in the markdown file header).

To prevent prefix drift, colons, or dashes (e.g., `Chương 1715: Thiên Ma Truyền Thuyết`), a robust programmatic hybrid guard will be integrated inside `scripts/update_book_metadata.py` to normalize the title before metadata updates.

## Proposed Changes

### 1. Centralized Verification Guard in `scripts/update_book_metadata.py`

Modify `scripts/update_book_metadata.py` to:
1. Accept `title_cn` as an optional 4th parameter.
2. If `title_cn` is provided, programmatically extract the chapter number `N` from the Chinese pattern `第\s*(\d+)\s*章`.
3. Strip any existing `Chương \d+`, leading colons, hyphens, dashes, and extra spaces from the translated title `title_vi`.
4. Format the final output title as: `Chương [N] [Cleaned Title]`.
5. Write the corrected title to `book.json`.

### 2. Enhanced Sub-Agent Instructions in `.agents/skills/translate-error-chapters/SKILL.md`

Update `SKILL.md` to:
1. Fetch and store the original Chinese title `title_cn` in the coordinator queue.
2. Include the `title_cn` in the self-contained Prompt payload constructed for each sub-agent.
3. Explicitly instruct the sub-agent on:
   - Converting the prefix `第[N]章` to `Chương [N]`.
   - Capitalizing the semantic title using Title Case (Sino-Vietnamese novel capitalization).
   - Composing `title_vi` using a single space separator: `Chương [N] [Title]` (no colons, hyphens, or dashes).
   - Writing the first line of the translated file exactly as `# [title_vi]` followed by a blank line.
4. Pass both the translated `title_vi` and the original `title_cn` to `scripts/update_book_metadata.py` in Step 3 of the orchestrator loop.

---

## Verification Plan

### Automated Verification
Run the improved update script with test cases to confirm formatting:
```bash
uv run python scripts/update_book_metadata.py "books/15112-indexhtml" 1672 "Chương 1715: Thiên Ma Truyền Thuyết" "第1715章 天魔传说"
```
Verify that `book.json` chapter index `1673` (array index `1672`) has `title_vi` set exactly to `Chương 1715 Thiên Ma Truyền Thuyết`.

### Manual Verification
Confirm that a sample translation run correctly formats the top line of the output `.txt` file as:
```markdown
# Chương 1715 Thiên Ma Truyền Thuyết
```
