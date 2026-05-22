---
name: translate-error-chapters
description: Use when a book has chapters with "error" status in book.json and they need high-quality Vietnamese translation using style guidelines.
---

# Translate Error Chapters (Orchestrator Mode)

## Overview
Systematically resolve translation pipeline errors by orchestrating the process via a sub-agent. The Main Agent acts as a lightweight coordinator (never reading the raw/translated text directly to preserve its context window), while a specialized sub-agent is spawned to read the files, perform the translation, and write the output file directly to disk.

> [!IMPORTANT]
> **Use Sub-Agent for Translation:** You must perform the translation by spawning a specialized sub-agent using the `invoke_subagent` tool. Do **NOT** read the raw source files or perform the translation in your own Main Agent session. This keeps your context footprint minimal and allows processing dozens of chapters in a single session.

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
1. Run a lightweight, Unicode-safe Python command (using `json.dumps()` to guarantee only basic ASCII characters are printed to avoid `UnicodeEncodeError` on Windows consoles) to cleanly fetch all error chapters in the book index `books/<book-dir>/book.json`:
   ```bash
   uv run python -c "import json; d = json.load(open('books/<book-dir>/book.json', encoding='utf-8')); print(json.dumps([(c['index'], c['id'], c['title_cn']) for c in d['chapters'] if c['status'] == 'error']))"
   ```
2. Note their sequential `"index"` field values (which are 1-based sequential identifiers), IDs, and raw titles.

### Step 2: Locate Source and Target Paths
1. Map the chapter's metadata `"index"` field value to the corresponding raw `.txt` file in `books/<book-dir>/raw/`.
   * **Rule:** The raw file name prefix is the 4-digit zero-padded representation of the `"index"` field value (e.g., if `"index"` is `683`, the raw file matches `0683_*.txt`).
2. Identify the target output file path: `books/<book-dir>/translating/<index_field_value>.txt`.
3. Locate the previous chapter's translated text path at `books/<book-dir>/translating/<index_field_value_minus_1>.txt` to pass as name/pronoun consistency context.

### Step 3: Dispatch Sub-Agent for Translation
1. Construct the detailed, self-contained prompt payload for the sub-agent. Fill in the exact absolute file paths for raw Chinese text, style guide, glossary, previous chapter, and target output.
2. Call the `invoke_subagent` tool with the constructed prompt payload.
3. The sub-agent will read the files, perform the translation in-context, write the completed Vietnamese text directly to disk at the output path, and return a lightweight JSON status object.

### Step 4: Verify Output File
1. Receive the JSON result from the sub-agent (e.g. `{"status": "success", "title_vi": "..."}`).
2. Verify the output file exists at the target path: `books/<book-dir>/translating/<index_field_value>.txt`.
3. Use the `view_file` tool on the target path, reading only the first 5 lines and the last 5 lines, to confirm the file was written successfully and contains high-quality Vietnamese text (ensuring no Chinese text blocks enter your own context).

### Step 5: Safe Programmatic Metadata Update
1. Update the chapter's metadata in `book.json` safely using the script utility.
   * **IMPORTANT:** The update utility script (`update_book_metadata.py`) expects the **0-based list array index** of the chapter, which is exactly the sequential `"index"` field value **minus 1** (e.g., if updating the chapter with `"index": 683`, you must pass `682` as the argument):
     ```bash
     uv run python scripts/update_book_metadata.py "books/<book-dir>" <index_field_value_minus_1> "<title_vi>"
     ```
2. Run a validation to verify `book.json` parsing is completely intact:
   ```bash
   uv run python -c "import json; json.load(open('books/<book-dir>/book.json', encoding='utf-8'))"
   ```

---

## Sub-Agent Translation Prompt Template

Copy, format, and execute this template via the `invoke_subagent` tool:

```markdown
You are a highly specialized Chinese-to-Vietnamese novel translator specializing in the **Tiên Hiệp (Xianxia)** genre. Your task is to produce a high-quality, professional translation of a chapter in-context.

## Context & Inputs
You must read the following files to get all necessary context, guidelines, and rules:
1. **Raw Chinese Text:** Read the raw source at `[Absolute Path to Raw Chinese File]`
2. **Style Guidelines:** Read `[Absolute Path to styles/tien_hiep.yaml]` for tone and translation rules.
3. **Glossary:** Read `[Absolute Path to books/<book-dir>/glossary.csv]` for terminology.
4. **Previous Chapter Context:** Read the last 1,000 characters of `[Absolute Path to books/<book-dir>/translating/<index-1>.txt]` to match pronouns (xưng hô) and name flows.

## Your Task Instructions:
1. **Layout & Scrambling Check:** Inspect the first 500 characters of the raw source. Check for scrambling, anti-scraping paragraphs, or ads, and reconstruct a clean text if necessary.
2. **Perform Translation:** Translate the entire Chinese source text into natural, high-quality Vietnamese prose.
   * Apply all genre guidelines and vocabulary rules from the style guidelines and glossary.
   * **Lexical Sandbox Rule:** DO NOT leak any English conjunctions, prepositions, or helper words (e.g., "but", "before", "not", "after", "while") into the translated Vietnamese output.
   * Maintain consistent name/pronoun styles matching the previous chapter context.
3. **Write Target File:** Write the complete translated Vietnamese text directly to `[Absolute Path to books/<book-dir>/translating/<index>.txt]`.
4. **Self-Review:** Read the written file to verify formatting matches, no raw Chinese remains, and that the Lexical Sandbox Rule was strictly adhered to.

## Output Format:
When complete, return ONLY a clean JSON object in the following format:
{
  "status": "success",
  "index": [Chapter Index],
  "title_vi": "[Translated Vietnamese Title]",
  "output_file": "[Absolute Path to books/<book-dir>/translating/<index>.txt]",
  "character_count": [Count]
}
```

---

## Common Mistakes

- **Reading raw/translated files in the Main Agent:** Reading files in the Main Agent ruins the "Orchestrator Mode" design, immediately flooding your context. Keep file-reading isolated to the sub-agent.
- **Modern vocabulary slip-ups:** Translating classical terms using modern everyday Vietnamese words (e.g., translating `长老` literally instead of "Trưởng lão").
- **English conjunction leakage:** Accidentally leaving words like "But", "Before", "Not" in the Vietnamese translation.
- **Forgetting context anchoring:** Translating a chapter in isolation without checking surrounding chapters, leading to character name drift (e.g. Claire, Bentley, Hoa Giáp Tử).
- **Fragile text search-and-replace on book.json:** Trying to edit the massive JSON file using regex, which causes syntax corruption. Always use `update_book_metadata.py` with the **0-based list array index** (`index - 1`).
- **Index off-by-one updates:** Passing the 1-based sequential `"index"` field value directly to `update_book_metadata.py`, which shifts the update to the next chapter and corrupts its metadata. Always pass `<index_field_value_minus_1>`.
