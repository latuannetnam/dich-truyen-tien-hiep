---
name: translate-error-chapters
description: Use when one or more chapters in books/<book-dir>/book.json have "error" or "crawled" status and need Vietnamese translation using tien_hiep style guidelines, glossary, and concurrent sub-agent orchestration.
---

# Translate Error Chapters (Concurrent Orchestrator Mode)

## Overview
Systematically resolve translation pipeline errors by orchestrating the process via specialized, isolated translation sub-agents. The Main Agent acts as a lightweight coordinator (never reading the raw/translated text directly to preserve its context window), while up to 3 concurrent sub-agents are spawned to read raw files, translate in-context using style guides and glossaries, write outputs directly to disk, and return lightweight JSON metadata.

> [!IMPORTANT]
> **Context Protection & Concurrency:** You must perform all translations by spawning specialized sub-agents using the `Agent` tool with a concurrency limit of 3. Do **NOT** read raw source files or generated Vietnamese files into your own Main Agent session. This keeps your context footprint minimal and allows processing dozens of chapters in a single session.

## When to Use
- **Trigger:** One or more chapters in `books/<book-dir>/book.json` have `"status": "error"` or `"status": "crawled"`.
- **Pre-requisite:** The raw Chinese text exists in `books/<book-dir>/raw/`.
- **Pre-requisite:** A translation style guideline exists (defaults to `tien_hiep` style at `styles/tien_hiep.yaml`).

Do **NOT** use when:
- All chapters are already `"translated"` (unless explicitly asked to re-translate).
- No raw Chinese source file is available.

---

## Core Pattern & Procedural Steps

### Step 1: Scan for target chapters
1. Run a lightweight, Unicode-safe Python command to cleanly fetch all error or crawled chapters in the book index `books/<book-dir>/book.json`:
   ```bash
   uv run python -c "import json; d = json.load(open('books/<book-dir>/book.json', encoding='utf-8')); result=[(c['index'], c['id'], c['title_cn'], c['status']) for c in d['chapters'] if c['status'] in ('error','crawled')]; open('scan_result.json','w',encoding='utf-8').write(json.dumps(result,ensure_ascii=False))"
   ```
2. Read `scan_result.json` to get the list of chapters needing translation.
3. Note their sequential `"index"` field values (which are 1-based sequential identifiers), IDs, and raw titles.

### Step 2: Establish the Coordination Queue
1. In your thought process log, construct a simple state tracker of all target chapters:
   * **Pending:** Chapters waiting to be translated, tracking sequential index, id, and raw `title_cn` from `book.json`.
   * **Active:** Chapters currently assigned to a running sub-agent task (maximum of 3).
   * **Completed:** Chapters successfully translated, saved, and updated.
   * **Failed:** Chapters where a sub-agent returned an error status.

### Step 2b: Single-Chapter Dispatch Mode (N=1)
If `len(target_chapters) == 1`:
1. Dispatch the single chapter with a direct `Agent` call (no sliding window needed).
2. After receiving the response, run the update command and verify.
3. Skip the sliding window loop entirely.

This simplifies observability and avoids unnecessary concurrency overhead for single-chapter runs.

### Step 3: Run the Sliding Window Concurrency Loop (N>1)
1. **Initial Dispatch:** Take up to the first 3 chapters from the **Pending** queue and dispatch them concurrently in a single turn using multiple `Agent` tool calls (use `run_in_background: true` for concurrent execution):
   ```json
   // First Agent call for chapter 1
   {
     "description": "Translate chapter 1",
     "prompt": "[Prompt filled with paths for chapter 1]",
     "subagent_type": "general-purpose",
     "run_in_background": true
   }
   // Second Agent call for chapter 2
   {
     "description": "Translate chapter 2",
     "prompt": "[Prompt filled with paths for chapter 2]",
     "subagent_type": "general-purpose",
     "run_in_background": true
   }
   // Third Agent call for chapter 3
   {
     "description": "Translate chapter 3",
     "prompt": "[Prompt filled with paths for chapter 3]",
     "subagent_type": "general-purpose",
     "run_in_background": true
   }
   ```
2. **Handle Incoming Metadata Responses:** As each sub-agent returns its JSON result:
   - **If Success:**
     1. Verify the file exists. Run `Read` reading only the first 3 lines of `books/<book-dir>/translating/<index>.txt` to verify successful generation without flooding your context.

     > [!WARNING]
     > **Serialized Updates & Index Offset Mapping:**
     > * **Serialized Lock:** To prevent race conditions and file stream crashes on Windows, you MUST run the update commands sequentially (one at a time) rather than in parallel shell streams.
     > * **Mathematical Index Mapping:** The update script expects the **0-based list array index**. Compute it as:
     >   ```
     >   array_index = sequential_index - 1
     >   ```
     >   Where `sequential_index` is the 1-based `index` field from `book.json`.
     > * **Example:** If updating chapter index `683` (from `book.json`), you must pass `682` to the script.

     ```bash
     uv run python scripts/update_book_metadata.py "books/<book-dir>" <array_index> "<title_vi>" "<title_cn>"
     ```

     > [!IMPORTANT]
     > **Audit-on-Write Verification Rule:**
     > Immediately inspect the stdout printout of the update script. The script prints:
     > `Successfully updated Chapter <Index> (<ID>):`
     > You MUST confirm that the `<Index>` in the printout matches your target chapter index. If it does not match (due to array alignment drift or off-by-one calculations), you must immediately restore `book.json` from git or backup and correct your index offset argument.

     3. Verify `book.json` syntax integrity:
        ```bash
        uv run python -c "import json; json.load(open('books/<book-dir>/book.json', encoding='utf-8')); open('book_valid.txt','w').write('ok')"
        ```
     4. Mark the chapter as **Completed** in your tracker.
   - **If Error:**
     1. Log the error and mark the chapter as **Failed** in your tracker.
   - **Fill the Sliding Window:** If there are still **Pending** chapters in your queue, immediately dispatch the next chapter in your list by calling `Agent` to maintain exactly 3 active sub-agents.
3. **Loop Termination:** Stop once all target chapters are marked either **Completed** or **Failed**.

### Progress Tracker (for multi-chapter runs)

Track progress using this lightweight structure:
```
{
  "pending": [4, 5, 6, 7, 8],
  "active": [{"index": 1, "dispatched_at": "..."}, {"index": 2, "dispatched_at": "..."}, {"index": 3, "dispatched_at": "..."}],
  "completed": [{"index": 1, "completed_at": "..."}],
  "failed": []
}
```

---

## Path Construction

Use `pathlib` for cross-platform absolute path construction:

```python
from pathlib import Path

book_dir = Path("books/15112-indexhtml")  # relative to repo root
raw_file = book_dir / "raw" / f"{chapter_index}.txt"           # books/15112-indexhtml/raw/3.txt
translating_file = book_dir / "translating" / f"{chapter_index}.txt"  # output destination
translated_file = book_dir / "translated" / f"{chapter_index}.txt"     # prior completed chapters
style_guide = Path("styles/tien_hiep.yaml")   # relative to repo root
glossary = book_dir / "glossary.csv"          # book-specific terminology
```

---

## Sub-Agent Execution Protocol & Sandbox Rules

The Main Agent must construct a detailed, self-contained `Prompt` payload for each sub-agent using this precise template. Replace the bracketed variables `[...]` with absolute file paths:

```markdown
You are a highly specialized Chinese-to-Vietnamese novel translator specializing in the **Tiên Hiệp (Xianxia)** genre. Your task is to produce a high-quality, professional translation of a chapter in-context.

## Context & Inputs
You must read the following files to get all necessary context, guidelines, and rules:
1. **Raw Chinese Text:** Read the raw source at `[Absolute Path to Raw Chinese File]`
2. **Style Guidelines:** Read `[Absolute Path to styles/tien_hiep.yaml]` for tone and translation rules.
3. **Glossary:** Read `[Absolute Path to books/<book-dir>/glossary.csv]` for terminology.
4. **Previous Chapter Context:** First check if `books/<book-dir>/translating/<index-1>.txt` exists.
   - **If YES:** Read the last 1,000 characters of `books/<book-dir>/translating/<index-1>.txt`
   - **If NO:** Read the last 1,000 characters of `books/<book-dir>/translated/<index-1>.txt`
   This ensures consistent pronouns (xưng hô) and name flows.
5. **Chinese Chapter Title:** The original Chinese title for this chapter is `[Chinese Chapter Title]` (from `book.json`).

## Your Task Instructions:
1. **Load Inputs:** Use the `Read` tool to read all of the files specified above. Report which files were successfully loaded in your JSON response's `files_loaded` array. If any file fails to load, add it to `files_failed`.
2. **Layout & Scrambling Check:** Inspect the first 500 characters of the raw source. Check for scrambling, anti-scraping paragraphs, or ads, and reconstruct a clean text if necessary.
3. **Translate Chapter Title & Content:**
   * **Title Translation Rule:** Translate the provided Chinese Chapter Title (`[Chinese Chapter Title]`) into a clean Vietnamese chapter title `title_vi` according to these strict rules:
     1. Convert the chapter number prefix: `第[N]章` must be translated to `Chương [N]`.
     2. Translate the remaining Chinese characters of the chapter title into natural, capitalized Sino-Vietnamese (Hán-Việt) or Vietnamese meaning (matching Tiên Hiệp/Xianxia style guidelines). Capitalize the first letter of every word (Title Case) (e.g. `天魔传说` -> `Thiên Ma Truyền Thuyết`).
     3. Combine the number prefix and translated title with a single space as a separator: `Chương [N] [Translated Title]` (e.g., `Chương 1715 Thiên Ma Truyền Thuyết`). Do NOT use colons (`:`), hyphens/dashes (`-` or `–`), or extra brackets around the chapter number.
     4. Set the `title_vi` field in your JSON output to this exact value.
   * **Translate Content:** Translate the entire Chinese source text into natural, high-quality Vietnamese prose.
     * Apply all genre guidelines and vocabulary rules from the style guidelines and glossary.
     * Maintain consistent name/pronoun styles matching the previous chapter context.
4. **Adhere to the Lexical Sandbox Rule:**
   * **Strict Constraint:** DO NOT leak any English conjunctions, prepositions, or helper words into the translated Vietnamese output.
   * **Programmatic Scan:** Before writing the file, you must explicitly scan your entire draft translation for common leaked English words. If any are found, replace them with their proper Vietnamese equivalents using this table:

   | Banned | Vietnamese Equivalent | Notes |
   |--------|---------------------|-------|
   | but | nhưng | |
   | and | và | |
   | or | hoặc | |
   | while | trong khi | |
   | before | trước khi | |
   | after | sau khi | |
   | of | của | |
   | to | đến / cho | depends on context |
   | in | trong | |
   | on | trên | |
   | at | tại | |
   | for | cho / vì | depends on context |
   | with | với | |
   | the | (omit article) | Vietnamese has no articles |
   | here | đây | |
   | now | bây giờ | |
   | okay | được / OK | |

5. **Write Target File:** Write the complete translated Vietnamese text directly to `[Absolute Path to books/<book-dir>/translating/<index>.txt]` using the `Write` tool (with overwrite set to true if replacing).
   * **Title Formatting in Content Rule:** The very first line of this file must contain the translated chapter title, formatted exactly as `# [title_vi]` (where `[title_vi]` is the translated chapter title, e.g., `# Chương 1715 Thiên Ma Truyền Thuyết`).
   * Ensure there is a blank line immediately after this first line.
6. **Self-Review:** Read the written file to verify:
   * The first line matches `# [title_vi]` exactly.
   * No raw Chinese remains.
   * The Lexical Sandbox Rule was strictly adhered to.

## Output Format:
When complete, return ONLY a clean JSON block in the following format:
```json
{
  "status": "success",
  "index": [Chapter Index],
  "title_vi": "[Translated Vietnamese Title]",
  "character_count": [Count],
  "translated_file_path": "[Absolute Path to books/<book-dir>/translating/<index>.txt]",
  "files_loaded": ["[Absolute Path to raw file]", "[Absolute Path to style guide]", "[Absolute Path to glossary]", "[Absolute Path to previous chapter context]"],
  "files_failed": [],
  "error_message": null
}
```

If an error occurs or the translation cannot be completed, return:
```json
{
  "status": "error",
  "index": [Chapter Index],
  "title_vi": null,
  "character_count": 0,
  "translated_file_path": "[Absolute Path to books/<book-dir>/translating/<index>.txt]",
  "files_loaded": [],
  "files_failed": ["[Path to failed file 1]", "[Path to failed file 2]"],
  "error_message": "[Error description]"
}
```
```

---

## Common Mistakes
- **Reading raw/translated files in the Main Agent:** Reading files in the Main Agent ruins the "Orchestrator Mode" design, immediately flooding your context. Keep file-reading strictly isolated to the sub-agent.
- **Index off-by-one updates:** Passing the 1-based sequential `"index"` field value directly to `update_book_metadata.py`, which shifts the update to the next chapter and corrupts its metadata. Always compute `array_index = sequential_index - 1`.
- **Modern vocabulary slip-ups:** Translating classical terms using modern everyday Vietnamese words (e.g., translating `长老` literally instead of "Trưởng lão").
- **English conjunction leakage:** Accidentally leaving words like "But", "Before", "Not" in the Vietnamese translation. Use the Vietnamese equivalents table to prevent this.
- **Fragile text search-and-replace on book.json:** Trying to edit the massive JSON file using regex, which causes syntax corruption. Always use `update_book_metadata.py` with the **0-based list array index** (`index - 1`).

---

## Title Normalization Guard

When `update_book_metadata.py` is called with 4 arguments (including `title_cn`), it runs a normalization guard on `title_vi`:

1. Extracts chapter number `N` from `title_cn` using regex `第\s*(\d+)\s*章`
2. Strips `Chương N`, colons, hyphens, dashes, and extra spaces from `title_vi`
3. Rebuilds as `Chương N {cleaned}`

**Example:**
- Input: `title_vi: "Chương 3: Ngã Phụ Tử"`, `title_cn: "第3章 我怕死"`
- Output: `title_vi: "Chương 3 Ngã Phụ Tử"`

The guard **preserves** the Sino-Vietnamese reading — it only strips punctuation and normalizes spacing. The Sino-Vietnamese `Ngã Phụ Tử` reading remains intact. The script does NOT convert Sino-Vietnamese to natural Vietnamese; it only removes colons, hyphens, and extra whitespace.