---
description: Translation engine, glossary system, chunking, TF-IDF term scoring, prompt structure
---

# Translation

## Key Files

| File | Purpose |
|------|---------|
| `translator/engine.py` | Main orchestration & chunking |
| `translator/llm.py` | OpenAI API wrapper, retry logic |
| `translator/style.py` | Style templates & priority loading |
| `translator/glossary.py` | Term management & auto-generation |
| `translator/term_scorer.py` | TF-IDF based glossary selection |

## TranslationEngine Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TranslationEngine                         │
│  ┌─────────────┐    ┌───────────┐    ┌──────────────────┐  │
│  │StyleTemplate│    │  Glossary │    │    LLMClient     │  │
│  │ - guidelines│    │ - entries │    │ - OpenAI SDK     │  │
│  │ - vocabulary│    │ - lookup  │    │ - retry logic    │  │
│  │ - examples  │    │ - export  │    │ - parallel calls │  │
│  └─────────────┘    └───────────┘    └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Sequential Chunking with Context

```
Chapter:  [====Chunk1====][====Chunk2====][====Chunk3====]
                ↓              ↓              ↓
Context:     (none)     [Trans-Chunk1]  [Trans-Chunk2]
                           (last 300c)    (last 300c)
                ↓              ↓              ↓
Output:   [==Trans1==]→[==Trans2==]→[==Trans3==]
```

- Chunks are translated **sequentially** (not parallel) per chapter
- Context = last 300 chars of previous chunk's **Vietnamese** output
- Chapter-level parallelism (N worker processes = N chapters at once)
- 20% overflow allowed to avoid splitting dialogue blocks

## Smart Dialogue Chunking

Dialogue blocks are kept together:
- Detects: Chinese quotes `""` `「」`, markers `说道`, `道：`, `问道`, `笑道`, `叫道`
- Consecutive dialogue paragraphs form one block
- Short narration (< 100 chars) between dialogues stays in block

## Glossary System

### Initial Generation

```
1. Sample N random chapters (TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS)
2. Take first M chars each (TRANSLATION_GLOSSARY_SAMPLE_SIZE)
3. LLM batch analysis (5 samples/batch) → extract names, locations, terms
4. Deduplicate → save to glossary.csv
```

### Progressive Building (Background)

```
Translator Worker → queues source path
Background Task (every 60s) → batch extract new terms
  → async lock → Glossary.add(new_terms) → save → version++
  → TermScorer.rebuild()
```

### TF-IDF Term Selection (per chunk)

```
Setup:   Read all chapters → compute IDF per term
         IDF = log(total_chapters / df)  (rarer = higher)

Per chunk: Find terms present → TF × IDF → top-N sent to LLM
```

## Translation Prompt Structure

```
SYSTEM:
  Role: Expert Chinese→Vietnamese translator
  Style Guidelines: [from style template]
  Vocabulary: [style vocabulary entries]

USER:
  Glossary (mandatory terms): [TF-IDF selected entries]
  Context (previous chunk output): "...last 300 chars..."
  Text to translate: [current chunk]
```

## Key Env Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRANSLATION_CHUNK_SIZE` | 2000 | Chars per chunk |
| `TRANSLATION_CHUNK_OVERLAP` | 300 | Context chars from previous chunk |
| `TRANSLATION_CONCURRENT_REQUESTS` | 3 | Max parallel API calls |
| `TRANSLATION_PROGRESSIVE_GLOSSARY` | true | Extract new terms during translation |
| `TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS` | 5 | Chapters to sample for initial glossary |
| `TRANSLATION_GLOSSARY_SAMPLE_SIZE` | 3000 | Characters per sample chapter |
