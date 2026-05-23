---
name: translate-error-chapters
description: Use when a book has chapters with "error" or "crawled" status in book.json and they need high-quality Vietnamese translation using style guidelines. Spawns up to 3 concurrent context-isolated sub-agents using a continuous sliding window to process translations safely and efficiently.
---

# Translate Error Chapters (Concurrent Orchestrator Mode)

## Overview
Systematically resolve translation pipeline errors by orchestrating the process via specialized, isolated translation sub-agents. The Main Agent acts as a lightweight coordinator (never reading the raw/translated text directly to preserve its context window), while up to 3 concurrent sub-agents are spawned to read raw files, translate in-context using style guides and glossaries, write outputs directly to disk, and return lightweight JSON metadata.

> [!IMPORTANT]
> **Context Protection & Concurrency:** You must perform all translations by spawning specialized sub-agents using the `invoke_subagent` tool with a concurrency limit of 3. Do **NOT** read raw source files or generated Vietnamese files into your own Main Agent session. This keeps your context footprint minimal and allows processing dozens of chapters in a single session.

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
   uv run python -c "import json; d = json.load(open('books/<book-dir>/book.json', encoding='utf-8')); print(json.dumps([(c['index'], c['id'], c['title_cn']) for c in d['chapters'] if c['status'] in ('error', 'crawled')]))"
   ```
2. Note their sequential `"index"` field values (which are 1-based sequential identifiers), IDs, and raw titles.

### Step 2: Establish the Coordination Queue
1. In your thought process log, construct a simple state tracker of all target chapters:
   * **Pending:** Chapters waiting to be translated, tracking sequential index, id, and raw `title_cn` from `book.json`.
   * **Active:** Chapters currently assigned to a running sub-agent task (maximum of 3).
   * **Completed:** Chapters successfully translated, saved, and updated.
   * **Failed:** Chapters where a sub-agent returned an error status.

### Step 3: Run the Sliding Window Concurrency Loop
1. **Initial Dispatch:** Take up to the first 3 chapters from the **Pending** queue and dispatch them concurrently in a single turn using the `invoke_subagent` tool:
   ```json
   invoke_subagent({
     "Subagents": [
       {
         "Prompt": "[Prompt filled with paths for chapter 1]",
         "Role": "Chinese-to-Vietnamese Xianxia Translator",
         "TypeName": "translator"
       },
       {
         "Prompt": "[Prompt filled with paths for chapter 2]",
         "Role": "Chinese-to-Vietnamese Xianxia Translator",
         "TypeName": "translator"
       },
       {
         "Prompt": "[Prompt filled with paths for chapter 3]",
         "Role": "Chinese-to-Vietnamese Xianxia Translator",
         "TypeName": "translator"
       }
     ]
   })
   ```
2. **Handle Incoming Metadata Responses:** As each sub-agent returns its JSON result:
   - **If Success:**
     1. Verify the file exists. Run `view_file` reading only the first 3 lines of `books/<book-dir>/translating/<index>.txt` to verify successful generation without flooding your context.
     
     > [!WARNING]
     > **Serialized Updates & Index Offset Mapping:**
     > * **Serialized Lock:** To prevent race conditions and file stream crashes on Windows, you MUST run the update commands sequentially (one at a time) rather than in parallel shell streams.
     > * **Mathematical Index Mapping:** The update script expects the **0-based list array index** of the chapter, which is exactly the sequential `"index"` field value **minus 1** (i.e. `0-based index = 1-based Chapter Index - 1`).
     > * **Example:** If updating chapter index `683`, you must pass `682` to the script:
     
     ```bash
     uv run python scripts/update_book_metadata.py "books/<book-dir>" <index_minus_1> "<title_vi>" "<title_cn>"
     ```
     
     > [!IMPORTANT]
     > **Audit-on-Write Verification Rule:**
     > Immediately inspect the stdout printout of the update script. The script prints:
     > `Successfully updated Chapter <Index> (<ID>):`
     > You MUST confirm that the `<Index>` in the printout matches your target chapter index. If it does not match (due to array alignment drift or off-by-one calculations), you must immediately restore `book.json` from git or backup and correct your index offset argument.
     
     3. Verify `book.json` syntax integrity:
        ```bash
        uv run python -c "import json; json.load(open('books/<book-dir>/book.json', encoding='utf-8'))"
        ```
     4. Mark the chapter as **Completed** in your tracker.
   - **If Error:**
     1. Log the error and mark the chapter as **Failed** in your tracker.
   - **Fill the Sliding Window:** If there are still **Pending** chapters in your queue, immediately dispatch the next chapter in your list by calling `invoke_subagent` to maintain exactly 3 active sub-agents.
3. **Loop Termination:** Stop once all target chapters are marked either **Completed** or **Failed**.

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
4. **Previous Chapter Context:** Read `[Absolute Path to books/<book-dir>/translating/<index-1>.txt]` if it exists, or fallback to the last 1,000 characters of `[Absolute Path to books/<book-dir>/translated/<index-1>.txt]` to match pronouns (xưng hô) and name flows.
5. **Chinese Chapter Title:** The original Chinese title for this chapter is `[Chinese Chapter Title]` (from `book.json`).

## Your Task Instructions:
1. **Load Inputs:** Use the `view_file` tool to read all of the files specified above.
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
   * **Programmatic Scan:** Before writing the file, you must explicitly scan your entire draft translation for common leaked English words (including: `but`, `here`, `now`, `okay`, `the`, `and`, `or`, `while`, `before`, `after`, `of`, `to`, `in`, `on`, `at`, `for`, `with`). If any are found, immediately replace them with their proper Vietnamese equivalents.
5. **Write Target File:** Write the complete translated Vietnamese text directly to `[Absolute Path to books/<book-dir>/translating/<index>.txt]` using the `write_to_file` tool (with `Overwrite` set to true if replacing).
   * **Title Formatting in Content Rule:** The very first line of this file must contain the translated chapter title, formatted exactly as `# [title_vi]` (where `[title_vi]` is the translated chapter title, e.g., `# Chương 1715 Thiên Ma Truyền Thuyết`).
   * Ensure there is a blank line immediately after this first line.
6. **Self-Review:** Read the written file to verify:
   * The first line matches `# [title_vi]` exactly.
   * No raw Chinese remains.
   * The Lexical Sandbox Rule was strictly adhered to.

## Output Format:
When complete, return ONLY a clean JSON block in the following format:
{
  "status": "success",
  "index": [Chapter Index],
  "title_vi": "[Translated Vietnamese Title]",
  "character_count": [Count],
  "translated_file_path": "[Absolute Path to books/<book-dir>/translating/<index>.txt]",
  "error_message": null
}

If an error occurs or the translation cannot be completed, return:
{
  "status": "error",
  "index": [Chapter Index],
  "title_vi": null,
  "character_count": 0,
  "translated_file_path": "[Absolute Path to books/<book-dir>/translating/<index>.txt]",
  "error_message": "[Error description]"
}
```

---

## Common Mistakes
- **Reading raw/translated files in the Main Agent:** Reading files in the Main Agent ruins the "Orchestrator Mode" design, immediately flooding your context. Keep file-reading strictly isolated to the sub-agent.
- **Index off-by-one updates:** Passing the 1-based sequential `"index"` field value directly to `update_book_metadata.py`, which shifts the update to the next chapter and corrupts its metadata. Always pass `<index_minus_1>`.
- **Modern vocabulary slip-ups:** Translating classical terms using modern everyday Vietnamese words (e.g., translating `长老` literally instead of "Trưởng lão").
- **English conjunction leakage:** Accidentally leaving words like "But", "Before", "Not" in the Vietnamese translation.
- **Fragile text search-and-replace on book.json:** Trying to edit the massive JSON file using regex, which causes syntax corruption. Always use `update_book_metadata.py` with the **0-based list array index** (`index - 1`).