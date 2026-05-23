# Design Document: Concurrent Sub-agent Translation Orchestration (Continuous Sliding Window)

**Date:** 2026-05-23  
**Status:** Approved  
**Topic:** Improving `.agents/skills/translate-error-chapters/SKILL.md` to utilize the Antigravity sub-agent feature with a 3-agent continuous sliding window workflow.

---

## 1. Goal & Context
When translating multiple error or crawled chapters, the Main Agent's context history easily gets flooded with thousands of tokens of raw Chinese text, vocabulary databases, and translated Vietnamese paragraphs. This causes context window overflow, slower execution, and instruction drift.

To resolve this, we transition the translation process to a **Concurrent Orchestrator-Worker model**:
1. **Main Agent** acts as the lightweight orchestrator: it never reads the text contents of the source files, style guidelines, or translations. It coordinates by scanning metadata, managing a 3-concurrency sliding window queue, passing paths to workers via `invoke_subagent`, and programmatically updating metadata.
2. **Sub-agents** are spawned concurrently (up to 3 in parallel) to read files, perform high-quality Tiên Hiệp translations, save files directly to the filesystem, and return only a compact JSON status object.

---

## 2. High-Level Architecture & Principles

```mermaid
graph TD
    MA[Main Agent / Orchestrator] -->|1. Scans Metadata| BJ[(book.json)]
    MA -->|2. Spawns Sub-Agent 1| SA1[Sub-Agent 1]
    MA -->|2. Spawns Sub-Agent 2| SA2[Sub-Agent 2]
    MA -->|2. Spawns Sub-Agent 3| SA3[Sub-Agent 3]
    
    subgraph Isolated Worker Contexts
        SA1 -->|Reads Raw / Context / Style / Glossary| Files1[(Filesystem)]
        SA1 -->|Translates & Saves| Out1[translating/101.txt]
        
        SA2 -->|Reads Raw / Context / Style / Glossary| Files2[(Filesystem)]
        SA2 -->|Translates & Saves| Out2[translating/102.txt]
        
        SA3 -->|Reads Raw / Context / Style / Glossary| Files3[(Filesystem)]
        SA3 -->|Translates & Saves| Out3[translating/103.txt]
    end
    
    SA1 -.-->|3. Returns JSON Metadata ONLY| MA
    SA2 -.-->|3. Returns JSON Metadata ONLY| MA
    SA3 -.-->|3. Returns JSON Metadata ONLY| MA
    
    MA -->|4. Updates Chapter Metadata| BJ
```

### Core Design Principles
* **Zero Raw Content Leakage:** The Main Agent never reads raw Chinese files or translated Vietnamese files. It only handles file paths.
* **Concurrent Execution (Limit = 3):** The Main Agent manages a continuous sliding window of exactly 3 active sub-agent invocations.
* **Incremental Metadata Updates:** When a sub-agent completes successfully, the Main Agent immediately updates `book.json` using `update_book_metadata.py` and dispatches the next pending chapter.

---

## 3. Detailed Orchestrator State Machine

The Main Agent tracks progress using a simple queue state structure in its thought/reasoning logs.

### Queue States
* **Pending:** Chapters needing translation (identified by status `error` or `crawled` in `book.json`).
* **Active:** Chapters currently being translated by a sub-agent task (maximum of 3).
* **Completed:** Chapters successfully translated, saved, and whose metadata in `book.json` has been updated.
* **Failed:** Chapters where the sub-agent returned an error.

### Sliding Window Execution Loop
1. **Initialize:** Parse `book.json` using a lightweight python command to get a list of all indices needing translation.
2. **First Dispatch:** Dispatch up to 3 parallel `invoke_subagent` calls for the first 3 chapters.
3. **Wait & Poll:** Wait for any sub-agent to return its response.
4. **Advance Sliding Window:** As each sub-agent returns its JSON result:
   - If **Success**:
     1. Verify the file exists.
     2. Update metadata in `book.json` by running `scripts/update_book_metadata.py` with arguments `index - 1` and `title_vi`.
     3. Verify `book.json` syntax integrity.
   - If **Error**:
     1. Log the error and mark the chapter as Failed.
   - If **Pending Chapters Remain**:
     1. Immediately dispatch the next chapter in the queue to maintain the 3-sub-agent concurrency.
5. **Terminate:** Stop when all target chapters are in either **Completed** or **Failed** states.

---

## 4. Sub-Agent Execution Protocol & Sandbox Rules

### Verified Antigravity Sub-agent Tool Call Signature
The Main Agent programmatically spawns sub-agents concurrently using the built-in `invoke_subagent` tool. This tool receives a `Subagents` array of objects, allowing the orchestrator to spawn up to 3 concurrent sub-agents in a single turn:

```json
invoke_subagent({
  "Subagents": [
    {
      "Prompt": "[Self-contained markdown prompt with absolute file paths]",
      "Role": "Chinese-to-Vietnamese Xianxia Translator",
      "TypeName": "translator"
    }
  ]
})
```

- **`Prompt`**: The detailed instruction prompt containing inputs, rules, and output format.
- **`Role`**: The defined persona / expertise of the sub-agent.
- **`TypeName`**: The sub-agent type/category (e.g., `translator`).
- **Context Isolation**: Each sub-agent runs in an isolated workspace session with a clean context window to prevent memory bloat.

### Sub-Agent Prompt Template
The Main Agent will construct the following detailed, self-contained prompt to be passed in the `Prompt` argument:

```markdown
You are a highly specialized Chinese-to-Vietnamese novel translator specializing in the **Tiên Hiệp (Xianxia)** genre. Your task is to produce a high-quality, professional translation of a chapter in-context.

## Context & Inputs
You must read the following files to get all necessary context, guidelines, and rules:
1. **Raw Chinese Text:** Read the raw source at `[Absolute Path to Raw Chinese File]`
2. **Style Guidelines:** Read `[Absolute Path to styles/tien_hiep.yaml]` for tone and translation rules.
3. **Glossary:** Read `[Absolute Path to books/<book-dir>/glossary.csv]` for terminology.
4. **Previous Chapter Context:** Read the last 1,000 characters of `[Absolute Path to books/<book-dir>/translating/<index-1>.txt]` to match pronouns (xưng hô) and name flows.

## Your Task Instructions:
1. **Load Inputs:** Use the `view_file` tool to read all of the files specified above.
2. **Layout & Scrambling Check:** Inspect the first 500 characters of the raw source. Check for scrambling, anti-scraping paragraphs, or ads, and reconstruct a clean text if necessary.
3. **Perform Translation:** Translate the entire Chinese source text into natural, high-quality Vietnamese prose.
   * Apply all genre guidelines and vocabulary rules from the style guidelines and glossary.
   * **Lexical Sandbox Rule:** DO NOT leak any English conjunctions, prepositions, or helper words (e.g., "but", "before", "not", "after", "while") into the translated Vietnamese output.
   * Maintain consistent name/pronoun styles matching the previous chapter context.
4. **Write Target File:** Write the complete translated Vietnamese text directly to `[Absolute Path to books/<book-dir>/translating/<index>.txt]` using the `write_to_file` tool (with `Overwrite` set to true if replacing).
5. **Self-Review:** Read the written file to verify formatting matches, no raw Chinese remains, and that the Lexical Sandbox Rule was strictly adhered to.

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

## 5. Verification Plan

### Manual Verification
1. Review the improved `.agents/skills/translate-error-chapters/SKILL.md` for clarity and consistency.
2. Verify all path mappings and scripts (like `update_book_metadata.py`) exist and behave as intended.
3. Confirm that the Main Agent instructions prevent reading any chapter files, ensuring strict memory/context preservation.
