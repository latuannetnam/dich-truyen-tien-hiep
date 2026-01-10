# Architecture & Mechanism Documentation

This document explains the internal workings and architecture of the Dịch Truyện translation tool.

## Overview

The application uses a **streaming pipeline architecture** with concurrent crawl and translation:

```
┌─────────────────────────────────────────────────────────────────┐
│                     StreamingPipeline                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐        UNBOUNDED                              │
│  │   Crawler    │──────▶  QUEUE  ──────▶ ┌─────────────────┐    │
│  │  (Producer)  │         (∞)            │ Translator      │    │
│  │              │       ┌────────────────│ Worker 1        │    │
│  │  Download    │       │                └─────────────────┘    │
│  │  chapters    │       │                ┌─────────────────┐    │
│  │  (never      │       └────────────────│ Translator      │    │
│  │   blocks)    │                        │ Worker 2        │    │
│  └──────────────┘                        └─────────────────┘    │
│        ↓                                 ┌─────────────────┐    │
│  Saves to disk                           │ Translator      │    │
│  immediately                             │ Worker 3        │    │
│                                          └─────────────────┘    │
│                                                                  │
│  ═══════════════════════════════════════════════════════════    │
│                              ▼                                   │
│                     ┌──────────────┐                            │
│                     │    EXPORT    │ (only when all_done=True)  │
│                     │ Direct EPUB  │                            │
│                     │ + Calibre    │                            │
│                     └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Unbounded Queue Design

The pipeline uses an **unbounded queue** (`maxsize=0`) between crawler and translators:

| Aspect | Behavior |
|--------|----------|
| **Crawler (Producer)** | Downloads chapters continuously, never blocks on queue |
| **Queue** | Unlimited size, stores chapter references (minimal memory) |
| **Translators (Consumers)** | Process chapters from queue at their own pace |
| **Resume** | Each chapter status saved to disk immediately after crawl/translate |

**Benefits:**
- Crawler can finish downloading all chapters while translation is still in progress
- No back-pressure blocking - maximizes download speed
- Interrupt-safe: status saved per-chapter, resume picks up where it left off

### Conditional Export

Auto-export only triggers when **all chapters are complete**:

```python
# Only export when:
# - All chapters in range translated
# - NOT cancelled by user (Ctrl+C)
should_export = result.all_done and not result.cancelled
```

If cancelled or incomplete, user sees:
```
Export skipped (cancelled by user)
Run 'dich-truyen export' to manually export available chapters
```

## Key Files Map

| Phase | Key Files | Purpose |
|-------|-----------|------------|
| **Pipeline** | `pipeline/streaming.py` | Concurrent crawl/translate orchestration |
| **Crawl** | `crawler/pattern.py` | LLM pattern discovery for CSS selectors |
| | `crawler/downloader.py` | Chapter download with resume support |
| | `crawler/base.py` | HTTP client with retry & encoding detection |
| **Translate** | `translator/engine.py` | Main translation orchestration & chunking |
| | `translator/llm.py` | OpenAI API wrapper with retry logic |
| | `translator/style.py` | Style templates & priority loading logic |
| | `translator/glossary.py` | Term management & auto-generation |
| | `translator/term_scorer.py` | TF-IDF based glossary selection |
| **Export** | `exporter/epub_assembler.py` | Direct EPUB assembly with parallel writing |
| | `exporter/calibre.py` | Calibre integration for AZW3/MOBI/PDF |
| **CLI** | `cli.py` | pipeline, export, glossary, style commands |
| **Config** | `config.py` | Pydantic settings & env vars |
| **Progress** | `utils/progress.py` | BookProgress & status data models |

## CLI Commands

```
dich-truyen
├── pipeline         # Main workflow (crawl + translate + export)
│   ├── --crawl-only
│   ├── --translate-only
│   └── --skip-export
├── export           # Standalone export
├── glossary
│   ├── export
│   ├── import
│   └── show
└── style
    ├── list
    └── generate
```

---

## Phase 1: Crawling

### LLM-Powered Pattern Discovery

The crawler uses LLM to automatically discover the structure of novel websites:

```python
# 1. Fetch index page HTML
html = await fetch(url, encoding)

# 2. LLM analyzes HTML structure
patterns = await llm.analyze_index_page(html)
# Returns: chapter_selector, encoding, has_pagination

# 3. Extract chapter list using discovered selector
chapters = soup.select(patterns.chapter_selector)
```

### Content Extraction Flow

```
Index Page HTML
      │
      ▼ (LLM analysis)
┌──────────────────────────┐
│ Discovered Patterns:     │
│ - chapter_selector       │
│ - content_selector       │
│ - title_selector         │
│ - elements_to_remove     │
└──────────────────────────┘
      │
      ▼ (for each chapter)
Chapter Page HTML ──▶ Extract content ──▶ Save as .txt
```

### Fallback Mechanism

When the LLM-discovered content selector fails (returns <100 chars), the system falls back to body extraction:

```python
# Primary: use discovered selector
content = soup.select_one(patterns.content_selector)

# Fallback: extract from body directly
if len(content) < 100:
    content = soup.find("body")
    # Filter navigation patterns (上一章, 下一章, etc.)
```

---

## Phase 2: Translation

### Translation Engine Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TranslationEngine                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌───────────┐    ┌──────────────────┐  │
│  │StyleTemplate│    │  Glossary │    │    LLMClient     │  │
│  │             │    │           │    │                  │  │
│  │ - guidelines│    │ - entries │    │ - OpenAI SDK     │  │
│  │ - vocabulary│    │ - lookup  │    │ - retry logic    │  │
│  │ - examples  │    │ - export  │    │ - parallel calls │  │
│  └─────────────┘    └───────────┘    └──────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Style Template System

Style templates define translation behavior and are loaded with priority:

1. **Custom styles** in `styles/` directory (checked first)
2. **Built-in styles** (fallback)

```yaml
name: tien_hiep
description: "Tiên hiệp, tu chân style"
guidelines:
  - "Use archaic pronouns: ta, ngươi, hắn"
  - "Keep cultivation terms: Kim Đan, Luyện Khí"
vocabulary:
  我: ta
  你: ngươi
  修炼: tu luyện
tone: archaic
examples:
  - chinese: "你是谁"
    vietnamese: "Ngươi là ai"
```

### Glossary System

#### Initial Glossary Generation

```
┌──────────────────────────────────────────────────────────┐
│              Glossary Generation Pipeline                 │
├──────────────────────────────────────────────────────────┤
│  1. Sample Selection                                      │
│     Select N random chapters (GLOSSARY_SAMPLE_CHAPTERS)  │
│                                                           │
│  2. Extract Content                                       │
│     Take first M chars from each (GLOSSARY_SAMPLE_SIZE)  │
│                                                           │
│  3. LLM Analysis (batched to avoid token limits)          │
│     Process in batches of 5 samples                       │
│     Request character names, locations, terms             │
│                                                           │
│  4. Merge & Save                                          │
│     Deduplicate entries, save to glossary.csv            │
└──────────────────────────────────────────────────────────┘
```

#### Progressive Glossary Building (Batch Mode)

New terms are extracted during translation and processed in the background to minimize overhead:

```
Translator Worker
       │
       ▼ (queues path)
[Pending Extraction Paths]
       │
       ▼ (Background Task)
Batch Extraction (every 60s)
       │
       ▼ (Extracts & Deduplicates)
Update Glossary (Thread-safe Lock)
       │
       ▼
Glossary Version++
Term Scorer Rebuild (if needed)
```

```python
# In TranslationWorker:
self._pending_extraction_paths.append(source_path)

# In Background Task:
new_terms = await extract_new_terms_from_chapter(content)
async with self._glossary_lock:
    glossary.add(new_terms)
    glossary.save()
```

#### TF-IDF Based Glossary Selection

Intelligent term selection using TF-IDF scoring - only includes glossary terms **relevant to each chunk**:

```
Setup Phase:
┌──────────────────────────────────────────────────────────┐
│  1. Read all chapter files                               │
│  2. For each glossary term, count how many chapters      │
│     contain it (Document Frequency)                      │
│  3. Calculate IDF = log(total_chapters / df)             │
│     Higher IDF = rarer term = more important             │
└──────────────────────────────────────────────────────────┘

Per Chunk:
┌──────────────────────────────────────────────────────────┐
│  1. Find glossary terms present in chunk                 │
│  2. Calculate TF = count of term in chunk                │
│  3. Score = TF × IDF                                     │
│  4. Select top-scoring terms (up to max_entries)         │
└──────────────────────────────────────────────────────────┘
```

```python
# Abstraction layer for future library replacement
class TermScorer(Protocol):
    def fit(documents: list[str], terms: list[str]) -> None
    def score_for_chunk(chunk: str) -> dict[str, float]
    def is_fitted() -> bool

# Current implementation: SimpleTermScorer (pure Python)
# Future: JiebaTermScorer, SklearnTermScorer
```

**Benefits:**
- **Token efficient**: Only relevant terms sent to LLM
- **Prioritizes rare terms**: Unique names/locations get higher scores
- **Automatic**: No manual configuration needed

### Smart Dialogue Chunking

Dialogue blocks are kept together to preserve conversation context:

```
Detection patterns:
- Chinese quotes: "" 「」
- Attribution markers: 说道, 道：, 问道, 笑道, 叫道

Behavior:
┌──────────────────────────────────────────┐
│ "你是谁？"陈平安问道。                    │  ← Dialogue block
│ "我是落落。"                              │    kept together
│ 少女轻声答道。                            │
└──────────────────────────────────────────┘
```

- Consecutive dialogue paragraphs form a block
- Short narration (<100 chars) between dialogues stays in block
- Allow 20% chunk overflow to avoid splitting conversations

### Sequential Chunk Translation with Context

Chapters are split into chunks but translated **sequentially** to maximize translation quality:

```
Chapter Text:  [====Chunk1====][====Chunk2====][====Chunk3====]
                      ↓              ↓              ↓
Processing:        Fast           Normal         Normal
                      ↓              ↓              ↓
Context:           (none)      [Trans-Chunk1] [Trans-Chunk2]
                                (Last 300 chars) (Last 300 chars)
                      ↓              ↓              ↓
Output:        [==Trans1==] → [==Trans2==] → [==Trans3==]
```

**Key design decisions:**
- **Sequential Processing**: Chunks are translated one by one.
- **Translated Context**: Each chunk receives the *translated Vietnamese* output of the previous chunk as context.
- **Benefit**: Drastically improves pronoun resolution (ta/ngươi/hắn) and terminological consistency compared to parallel translation.
- **Performance**: Chapter-level parallelism (multiple workers processing different chapters) maintains high overall throughput.

### Translation Prompt Structure

```
┌─────────────────────────────────────────┐
│            SYSTEM PROMPT                │
├─────────────────────────────────────────┤
│ Role: Expert Chinese-Vietnamese         │
│       translator                        │
│                                         │
│ Style Guidelines:                       │
│ - [guidelines from style template]      │
│                                         │
│ Vocabulary:                             │
│ - 修炼 → tu luyện                       │
│ - 灵气 → linh khí                       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│            USER PROMPT                  │
├─────────────────────────────────────────┤
│ Glossary (mandatory terms):             │
│ - 陈平安 → Trần Bình An                  │
│                                         │
│ Context (from previous chunk's output): │
│ "...người thiếu niên đeo kiếm..."       │
│                                         │
│ Text to translate:                      │
│ [current chunk content]                 │
└─────────────────────────────────────────┘
```

---

## Phase 3: Export

### Direct EPUB Assembly

The export phase creates EPUB files directly from translated chapters using parallel processing:

```
Translated Chapters (/translated/*.txt)
              │
              ▼ (parallel file writing)
┌──────────────────────────────────────────────────────────┐
│    DirectEPUBAssembler                                   │
│                                                          │
│    ThreadPool (8 workers):                               │
│    ├── Worker 1: chapter_0001.xhtml                      │
│    ├── Worker 2: chapter_0002.xhtml                      │
│    ├── ...                                               │
│    └── Worker 8: chapter_0008.xhtml                      │
│                                                          │
│    Generate: content.opf, toc.ncx, styles.css            │
│    ZIP → book.epub                                       │
└──────────────────────────────────────────────────────────┘
              │
              ▼ (if format ≠ epub)
┌──────────────────────────────────────────────────────────┐
│    Calibre Conversion: EPUB → AZW3/MOBI/PDF              │
└──────────────────────────────────────────────────────────┘
              │
              ▼
         book.azw3 (or other format)
```

### EPUB Structure Generated

```
epub_build/
├── mimetype                    # "application/epub+zip"
├── META-INF/
│   └── container.xml           # Points to content.opf
└── OEBPS/
    ├── content.opf             # Manifest + spine
    ├── toc.ncx                 # Navigation
    ├── styles.css              # Shared CSS
    ├── titlepage.xhtml         # Title page
    └── chapters/
        ├── chapter_0001.xhtml
        ├── chapter_0002.xhtml
        └── ... (all chapters)
```

### Parallel Chapter Writing

```python
class DirectEPUBAssembler:
    async def assemble(self, book_dir, chapters):
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Write chapter files in parallel
            tasks = [
                loop.run_in_executor(
                    executor,
                    self._write_chapter_file,
                    chapters_dir, index, chapter
                )
                for index, chapter in enumerate(chapters, 1)
            ]
            await asyncio.gather(*tasks)
        
        # Generate manifest and TOC
        self._write_manifest(oebps_dir, chapters)
        self._write_toc(oebps_dir, chapters)
        
        # ZIP into EPUB
        self._create_epub_zip(work_dir, epub_path)
```

### Progress Display

```
Assembling EPUB with 1200 chapters...
Writing chapters... [450/1200] ━━━━━━━━━━━━━━━━━ 38%
Generating manifest... ━━━━━━━━━━━━━━━━━━━━━━━━━━ 95%
Creating EPUB archive... ━━━━━━━━━━━━━━━━━━━━━━━ 98%
Converting to AZW3... ━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
```

### Calibre Integration

For non-EPUB formats, Calibre converts the generated EPUB:

```python
# EPUB → AZW3 is much faster than HTML → AZW3
exporter.export(
    input_html=epub_path,  # EPUB as input
    output_format="azw3",
)
```

**Supported formats:** EPUB, AZW3 (Kindle), PDF, MOBI

---

## Progress Tracking

### BookProgress Model

```python
class BookProgress(BaseModel):
    url: str                    # Source URL
    title: str                  # Original Chinese title
    title_vi: str               # Vietnamese title
    author: str                 # Original author name
    author_vi: str              # Vietnamese author name
    encoding: str               # Content encoding
    patterns: BookPatterns      # Discovered selectors
    chapters: list[Chapter]     # Chapter list with status
```

### Chapter Status Flow

```
PENDING ──▶ CRAWLED ──▶ TRANSLATED
    │           │            │
    └───────────┴────────────┴──▶ ERROR (if failed)
```

### Resumable Operations

Both crawling and translation save progress **after each chapter**:

```python
# Resume mode (default): skip completed chapters
if resume:
    chapters_to_process = [c for c in chapters if c.status == PENDING]

# Force mode: re-process all chapters
if force:
    chapters_to_process = all_chapters

# Progress saved after each chapter
progress.save(book_dir)  # Prevents data loss on interruption
```

---

## Progress Display

### Live Table (In-Place Updates)

The pipeline uses Rich's `Live` display to show a table that updates **in place** without scrolling:

```
                     Translate: 5/11 (45%)
 Crawl                      Worker 1                         Worker 2                         Worker 3                       
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 8/10 (80%)                 Ch.3: 第3章... 1/2 [1]            Ch.4: 第4章... 0/2               Ch.5: 第5章... 1/2 [1]         
 Ch.9: 第九章...                                              translating [1,2]                                               
                                     Glossary: 85 entries | Glossary generated
```

### Key Techniques

1. **Rich `Live` Context Manager**
   ```python
   from rich.live import Live
   
   with Live(build_table(), console=console, refresh_per_second=0.5, transient=True) as live:
       async def update_display():
           while not stop_requested:
               live.update(build_table())  # Rebuild table with current stats
               await asyncio.sleep(1)
   ```

2. **Transient Mode**: `transient=True` makes the Live display disappear when complete, leaving clean output.

3. **Table Title for Progress**: Translate progress shown as table title (updates in place):
   ```python
   table = Table(title=f"Translate: {translated}/{total} ({pct}%)")
   ```

4. **Table Caption for Status**: Glossary count and status messages shown in caption:
   ```python
   table = Table(caption="Glossary: 85 entries | Glossary generated")
   ```

5. **Avoid Console Prints During Live**: Any `console.print()` during Live display causes scrolling. Instead:
   - Store status in `PipelineStats.status_message` and `PipelineStats.glossary_count`
   - Display in table caption, which updates in place

### Worker Status Format

Each worker column shows:
```
Ch.3: 第3章 领取杂务（大修）... 1/2 [1]
       ↑                       ↑    ↑
   Chapter title          Done/Total  Active chunk
```

Status values: `idle` → `translating [1,2]` → `1/2 [1]` → `done`

---

## Configuration

### Pydantic Settings

```python
class AppConfig(BaseSettings):
    llm: LLMConfig           # OPENAI_* env vars
    crawler: CrawlerConfig   # CRAWLER_* env vars
    translation: TranslationConfig  # TRANSLATION_* env vars
    calibre: CalibreConfig   # CALIBRE_* env vars
    export: ExportConfig     # EXPORT_* env vars
```

### Environment Variables

| Prefix | Purpose |
|--------|---------|
| `OPENAI_` | LLM API configuration (API_KEY, BASE_URL, MODEL) |
| `CRAWLER_` | HTTP client settings (delay, retries, timeout) |
| `TRANSLATION_` | Translation & glossary settings |
| `CALIBRE_` | Ebook converter path |
| `EXPORT_` | Export settings (parallel workers, fast mode) |

#### Key Translation Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRANSLATION_CHUNK_SIZE` | 2000 | Characters per translation chunk |
| `TRANSLATION_CHUNK_OVERLAP` | 300 | Context chars from previous chunk |
| `TRANSLATION_CONCURRENT_REQUESTS` | 3 | Max parallel API calls |
| `TRANSLATION_PROGRESSIVE_GLOSSARY` | true | Extract new terms during translation |
| `TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS` | 5 | Chapters to sample for initial glossary |
| `TRANSLATION_GLOSSARY_SAMPLE_SIZE` | 3000 | Characters per sample chapter |

#### Key Export Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `EXPORT_PARALLEL_WORKERS` | 8 | Threads for parallel chapter file writing |
| `EXPORT_VOLUME_SIZE` | 0 | Chapters per volume (0 = single book) |
| `EXPORT_FAST_MODE` | true | Use direct EPUB assembly |

---

## File Structure

```
books/
└── 8717-indexhtml/
    ├── book.json           # BookProgress serialized
    ├── glossary.csv        # Term translations
    ├── raw/                # Downloaded chapters
    │   ├── 0001_第一章-惊蛰.txt
    │   └── ...
    ├── translated/         # Translated chapters
    │   ├── 1.txt
    │   └── ...
    ├── epub_build/         # EPUB build directory (auto-generated)
    │   ├── mimetype
    │   ├── META-INF/
    │   └── OEBPS/
    │       ├── chapters/   # Chapter XHTML files
    │       ├── content.opf
    │       └── toc.ncx
    └── output/
        ├── book.epub       # Generated EPUB
        └── book.azw3       # Converted ebook
```

---

## Error Handling

### Retry Logic

All network operations use exponential backoff:

```python
for attempt in range(max_retries):
    try:
        response = await client.get(url)
        return response
    except Exception:
        await sleep(delay * (2 ** attempt))  # 1s, 2s, 4s...
```

### Graceful Degradation

- **Content extraction:** Falls back to `<body>` if selector fails
- **Encoding detection:** Uses chardet if specified encoding fails
- **Glossary parsing:** Returns empty list if LLM response invalid
- **Progressive glossary:** Silently fails (non-blocking enhancement)
