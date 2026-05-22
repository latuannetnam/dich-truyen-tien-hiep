# Design Document: Sub-agent Translation Orchestration (Orchestrator Mode)

**Date:** 2026-05-22  
**Status:** Approved  
**Topic:** Transitioning `translate-error-chapters` skill to use a sub-agent for translation, saving the file, and returning the result.

---

## 1. Goal & Context
When translating multiple error chapters in a single session, the Main Agent's context history easily gets flooded with thousands of tokens of raw Chinese text, vocabulary databases, and translated Vietnamese paragraphs. This leads to context window overflow, slow response times, and failure to follow instructions.

To optimize context usage, we transition the translation process to a **pure orchestrator/sub-agent model (Orchestrator Mode)**:
1. **Main Agent** acts as the orchestrator: it never reads the text contents of the source files, style guidelines, or translations. It only coordinates by scanning metadata, passing file paths to a translation sub-agent via `invoke_subagent`, and programmatically updating metadata.
2. **Sub-agent** is spawned to perform the actual resource-intensive translation task, saving the file directly to the disk, and returning only a tiny JSON status payload.

---

## 2. Proposed Changes

### Modify `.agents/skills/translate-error-chapters/SKILL.md`
We will rewrite `SKILL.md` to:
- Establish the **Orchestrator Mode** architecture.
- Structure step-by-step instructions for the **Main Agent** to act as a pure path coordinator.
- Provide a robust, self-contained **Sub-Agent Translation Prompt Template** that the Main Agent copies and executes via `invoke_subagent`.
- Define step-by-step instructions for the sub-agent to load paths, translate, write to the filesystem, and return a lightweight JSON object.
- Detail the lightweight metadata verification and safe execution steps using `update_book_metadata.py`.

---

## 3. Detailed Orchestrator Design

### Main Agent Workflow (Lightweight)
1. **Scan `book.json`:** Fetch error chapters using the Unicode-safe python command.
2. **Construct paths:** Zero-pad the index to locate the raw file, locate previous translated text, locate guidelines and glossaries.
3. **Dispatch Sub-agent:** Use `invoke_subagent` tool with the detailed template prompt.
4. **Receive response:** Sub-agent returns success status and `title_vi`.
5. **Verify:** Check the output file on disk exists and contains translated text.
6. **Update Metadata:** Run `scripts/update_book_metadata.py` with `index - 1`.

### Sub-Agent Prompts & Responsibilities
The sub-agent is instructed to:
1. **Read files:** Use `view_file` to read the raw text, guidelines, glossary, and previous context paths provided in the payload.
2. **Translate:** Perform high-quality Tiên Hiệp translation, respecting the Lexical Sandbox Rule (no English prepositions/conjunctions).
3. **Save File:** Use `write_to_file` to write the output directly to `books/<book-dir>/translating/<index_field_value>.txt`.
4. **Respond:** Return a small JSON payload.

---

## 4. Verification Plan

### Manual Verification
1. We will verify the syntax and clarity of the updated `SKILL.md` file.
2. We will run the linter / tests to ensure the workspace remains stable.
