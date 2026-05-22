---
name: translate-error-chapters
description: Use when a book has chapters with "error" status in book.json and they need high-quality Vietnamese translation using style guidelines.
---

# Translate Error Chapters

## Overview
Systematically resolve translation pipeline errors by reading the raw Chinese source, applying genre-specific style templates in-context, translating with lexical sandboxing, and updating metadata programmatically.

> [!IMPORTANT]
> **Use Model Capability Only:** You must perform the translation directly in-context using your own advanced language model capabilities. Do **NOT** run project python scripts, command-line translation tools (such as `uv run dich-truyen translate`), or any project codebase functionality to perform the translation. All translations must be generated solely by your model execution.

## When to Use
- **Trigger:** A chapter in `books/<book-dir>/book.json` has `"status": "error"`.
- **Pre-requisite:** The raw Chinese text exists in `books/<book-dir>/raw/`.
- **Pre-requisite:** A translation style guideline exists (e.g. `styles/tien_hiep.yaml`).

Do **NOT** use when:
- The chapter status is already `"translated"` (unless explicitly asked to re-translate).
- No raw Chinese source file is available.

---

## Core Pattern & Procedural Steps

### Step 1: Scan for Errors
1. Run a lightweight, Unicode-safe Python command (using `json.dumps()` to guarantee only basic ASCII characters are printed to avoid `UnicodeEncodeError` on Windows consoles using CP1252/ASCII encoding defaults) to cleanly fetch all error chapters in the book index `books/<book-dir>/book.json`:
   ```bash
   uv run python -c "import json; d = json.load(open('books/<book-dir>/book.json', encoding='utf-8')); print(json.dumps([(c['index'], c['id'], c['title_cn']) for c in d['chapters'] if c['status'] == 'error']))"
   ```
2. Note their sequential `"index"` field values (which are 1-based sequential identifiers), IDs, and raw titles.

### Step 2: Locate Source and Style Rules
1. Map the chapter's metadata `"index"` field value to the corresponding raw `.txt` file in `books/<book-dir>/raw/`.
   * **Rule:** The raw file name prefix is the 4-digit zero-padded representation of the `"index"` field value (e.g., if `"index"` is `683`, the raw file matches `0683_*.txt`).
2. Read the designated style guide (e.g., `styles/tien_hiep.yaml`). Extract rules from `guidelines`, term mappings from `vocabulary`, and `tone`.

### Step 3: Layout Check & Translation
1. **Pre-flight Layout Analysis**: Inspect the first 500 characters of the raw text. Check for scrambling (e.g. jumbled sentences, anti-scraping alternating paragraphs, or garbage ads). If scrambled, reconstruct the coherent text first.
2. **Context Integration**: Read the last 1,000 characters of the *previously translated* chapter to maintain terminology, names (e.g. 花甲子 to Hoa Giáp Tử), xưng hô (pronouns), and flow.
3. **Glossary Loading**: Pull key vocabulary terms from `glossary.csv` that occur in the target chapter.
4. **Translation Execution**:
   - Translate the entire chapter in a single pass if it is under 5,000 characters to preserve context and prose continuity.
   - For extra long chapters (>5,000 characters), split into chunks of 3,000 characters with a 400-character overlap, injecting the previous chunk's translated Vietnamese output as context.
   - **Lexical Sandbox Rule**: Enforce a strict system constraint: *DO NOT leak any English conjunctions, prepositions, or helper words (e.g., "but", "before", "not", "after") into the translated Vietnamese output.*

### Step 4: Write Translated Text
1. Write the completed Vietnamese text to `books/<book-dir>/translating/<index_field_value>.txt` (named exactly after the value of the `"index"` field in the chapter's metadata object in `book.json`; e.g., if the chapter object's `"index"` field value is `683`, save as `translating/683.txt`).
2. Verify formatting matches the source paragraphs, and run a quick check to ensure no English words leaked.

### Step 5: Safe Programmatic Metadata Update
1. Translate `title_cn` of the chapter to `title_vi` using Tiên Hiệp conventions.
2. Update the chapter's metadata in `book.json` safely using the script utility.
   * **IMPORTANT:** The update utility script (`update_book_metadata.py`) expects the **0-based list array index** of the chapter, which is exactly the sequential `"index"` field value **minus 1** (e.g., if updating the chapter with `"index": 683`, you must pass `682` as the argument):
     ```bash
     uv run python scripts/update_book_metadata.py "books/<book-dir>" <index_field_value_minus_1> "<title_vi>"
     ```
3. Run a validation to verify `book.json` parsing is completely intact:
   ```bash
   uv run python -c "import json; json.load(open('books/<book-dir>/book.json', encoding='utf-8'))"
   ```

---

## Common Mistakes

- **Modern vocabulary slip-ups:** Translating classical terms using modern everyday Vietnamese words (e.g., translating `长老` literally instead of "Trưởng lão").
- **English conjunction leakage:** Accidentally leaving words like "But", "Before", "Not" in the Vietnamese translation.
- **Forgetting context anchoring:** Translating a chapter in isolation without checking surrounding chapters, leading to character name drift (e.g. Claire, Bentley, Hoa Giáp Tử).
- **Fragile text search-and-replace on book.json:** Trying to edit the massive JSON file using regex, which causes syntax corruption. Always use `update_book_metadata.py` with the **0-based list array index** (`index - 1`).
- **Index off-by-one updates:** Passing the 1-based sequential `"index"` field value directly to `update_book_metadata.py`, which shifts the update to the next chapter and corrupts its metadata. Always pass `<index_field_value_minus_1>`.