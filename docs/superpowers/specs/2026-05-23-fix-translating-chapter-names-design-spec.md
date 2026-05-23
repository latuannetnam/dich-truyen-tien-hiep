# Design Spec: Fix Translating Chapter Names

## Overview
This specification details the plan to fix the chapter prefix mismatch issue in the `translating/` folder for the book `15112-indexhtml`.

## Background & Problem
For the book `15112-indexhtml`, multiple chapter files in the `books/15112-indexhtml/translating/` folder contain incorrect chapter numbers on their first lines. Specifically, files `1622.txt` through `1691.txt` use their 1-based sequential file index (e.g. `Chương 1622: Cấp Tai Họa`) instead of the correct Chinese chapter numbers (e.g. `Chương 1664: Cấp Tai Họa`) defined in `book.json`.

We need a one-off utility script to systematically correct these first lines in `books/15112-indexhtml/translating/` to restore synchronization with the metadata defined in `book.json`.

## Proposed Solution
We will implement a Python utility script under `scratch/fix_chapter_names.py` that will:
1. Load `books/15112-indexhtml/book.json` to get the metadata.
2. Scan the `books/15112-indexhtml/translating/` folder for `.txt` files.
3. For each file `[index].txt`:
   - Parse the 1-based sequential `index` (e.g. `1622` from `1622.txt`).
   - Match it against the chapter with the same `"index"` in `book.json`.
   - Parse the correct Chinese chapter number from `title_cn` (e.g. `第1664章` -> `1664`).
   - Read the file content.
   - Extract the title suffix from the current first line (e.g. `Cấp Tai Họa` from `Chương 1622: Cấp Tai Họa`).
   - Construct the corrected first line: `Chương <num>: <title_suffix>`.
   - Update only the first line of the file, preserving all subsequent lines, paragraphs, and original line endings.
   - Write the file back to `books/15112-indexhtml/translating/[index].txt` in UTF-8 encoding.
4. Support a `--dry-run` parameter (default `True` for safety) to log matches and preview modifications without executing write operations.
5. Support an `--execute` parameter to commit the changes.

## Verification Plan
1. **Dry-Run Analysis**: Run the script with `--dry-run` and review the printed mapping of matches. Verify that all 70 mismatches are correctly mapped.
2. **Execution**: Run the script with `--execute`.
3. **Post-Execution Scan**: Run `scratch/check_translating.py` to confirm that the number of mismatched files in the `translating/` directory drops to 0.
4. **Content Sanity Check**: Read the first few lines of a sample of modified files (e.g. `1622.txt`, `1645.txt`) to ensure the line endings, title prefix, title suffix, and colons are perfectly formed.
