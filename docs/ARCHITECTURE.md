# Architecture & Mechanism Documentation

This document explains the internal workings and architecture of the Dịch Truyện translation tool.

## Overview

The application follows a 4-phase pipeline architecture:

```
┌─────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│  CRAWL  │────▶│ TRANSLATE │────▶│  FORMAT  │────▶│  EXPORT  │
│         │     │           │     │          │     │          │
│ Download│     │  Chinese  │     │  HTML    │     │  EPUB    │
│ chapters│     │    to     │     │ assembly │     │  AZW3    │
│ from web│     │Vietnamese │     │  + TOC   │     │  PDF     │
└─────────┘     └───────────┘     └──────────┘     └──────────┘
```

## Key Files Map

| Phase | Key Files | Purpose |
|-------|-----------|---------|
| **Crawl** | `crawler/pattern.py` | LLM pattern discovery for CSS selectors |
| | `crawler/downloader.py` | Chapter download with resume support |
| | `crawler/base.py` | HTTP client with retry & encoding detection |
| **Translate** | `translator/engine.py` | Main translation orchestration & chunking |
| | `translator/llm.py` | OpenAI API wrapper with retry logic |
| | `translator/style.py` | Style templates & priority loading logic |
| | `translator/glossary.py` | Term management & auto-generation |
| **Format** | `formatter/assembler.py` | HTML book assembly with TOC generation |
| | `formatter/metadata.py` | Book metadata handling |
| **Export** | `exporter/calibre.py` | Calibre ebook-convert integration |
| **CLI** | `cli.py` | All CLI commands implementation |
| **Config** | `config.py` | Pydantic settings & env vars |
| **Progress** | `utils/progress.py` | BookProgress & status data models |

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

#### Progressive Glossary Building

New terms are extracted during translation to build glossary incrementally:

```
Ch.1 translated...
  +2 new glossary terms (刘羡阳 → Lưu Tiện Dương)
Ch.2 translated...
  +1 new glossary terms (宁姚 → Ninh Diêu)
```

```python
# After each chapter translation (if TRANSLATION_PROGRESSIVE_GLOSSARY=true):
new_terms = await extract_new_terms_from_chapter(
    chinese_text, existing_glossary, max_new_terms=3
)
glossary.add(new_terms)
glossary.save(book_dir)  # Auto-save after each chapter
```

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

### Parallel Chunk Translation

Large chapters are split into chunks and translated **in parallel** for speed:

```
Chapter Text:  [====Chunk1====][====Chunk2====][====Chunk3====]
                      ↓              ↓              ↓
Context:           (none)    ←300 chars→    ←300 chars→
                      ↓              ↓              ↓
               ┌─────────────────────────────────────────┐
               │   Parallel Translation (semaphore)      │
               │   TRANSLATION_CONCURRENT_REQUESTS=3     │
               └─────────────────────────────────────────┘
                      ↓              ↓              ↓
Output:        [==Trans1==] + [==Trans2==] + [==Trans3==]
```

**Key design decisions:**
- Context uses **source Chinese** text (not translated output) to enable parallel processing
- Each chunk receives ~300 chars from previous chunk for narrative continuity
- Semaphore limits concurrent API calls to respect rate limits
- Results sorted by index to maintain correct order

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
│ Context (from previous chunk):          │
│ "...last 300 chars of Chinese source..."│
│                                         │
│ Text to translate:                      │
│ [current chunk content]                 │
└─────────────────────────────────────────┘
```

---

## Phase 3: Formatting

### HTML Assembly

```python
class HTMLAssembler:
    def assemble(self):
        # 1. Load book metadata (title_vi, author_vi)
        metadata = BookMetadataManager.from_book_progress(progress)
        
        # 2. Generate HTML header with CSS
        html = generate_header(metadata)
        
        # 3. Add title page
        html += generate_title_page(metadata)
        
        # 4. Generate TOC with chapter links
        html += generate_toc(chapters)
        
        # 5. Add each chapter with Vietnamese titles
        for chapter in chapters:
            html += format_chapter(chapter)
        
        # 6. Save to formatted/book.html
        save(html)
```

### Metadata Translation

Book metadata is automatically translated during the translation phase:

```python
# Translates book title and author name to Vietnamese
if not progress.title_vi:
    progress.title_vi = await llm.translate_title(progress.title, "book")
    progress.author_vi = await llm.translate_title(progress.author, "author")
```

---

## Phase 4: Export

### Calibre Integration

```python
class CalibreExporter:
    def export(self, book_dir, output_format):
        # 1. Build Calibre command
        cmd = [
            "ebook-convert",
            "formatted/book.html",
            f"output/book.{output_format}",
            "--title", metadata.title,
            "--authors", metadata.author,
        ]
        
        # 2. Execute conversion
        result = subprocess.run(cmd)
        
        # 3. Return result path
        return output_path
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

### Parallel Translation Indicator

```
Ch.1: 第一章 惊蛰... translating [1,2,3] [0/6] ━━━━━━━━━━━   0%
                              ↑
                     Active parallel chunks

Ch.1: 第一章 惊蛰... [done] [6/6] ━━━━━━━━━━━━━━━━━━━━━━━━ 100%
```

The progress bar:
1. Pre-calculates total chunks across all chapters
2. Shows active parallel chunks (e.g., `translating [1,2,3]`)
3. Advances by 1 after each chunk completes

---

## Configuration

### Pydantic Settings

```python
class AppConfig(BaseSettings):
    llm: LLMConfig           # OPENAI_* env vars
    crawler: CrawlerConfig   # CRAWLER_* env vars
    translation: TranslationConfig  # TRANSLATION_* env vars
    calibre: CalibreConfig   # CALIBRE_* env vars
```

### Environment Variables

| Prefix | Purpose |
|--------|---------|
| `OPENAI_` | LLM API configuration (API_KEY, BASE_URL, MODEL) |
| `CRAWLER_` | HTTP client settings (delay, retries, timeout) |
| `TRANSLATION_` | Translation & glossary settings |
| `CALIBRE_` | Ebook converter path |

#### Key Translation Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRANSLATION_CHUNK_SIZE` | 2000 | Characters per translation chunk |
| `TRANSLATION_CHUNK_OVERLAP` | 300 | Context chars from previous chunk |
| `TRANSLATION_CONCURRENT_REQUESTS` | 3 | Max parallel API calls |
| `TRANSLATION_PROGRESSIVE_GLOSSARY` | true | Extract new terms during translation |
| `TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS` | 5 | Chapters to sample for initial glossary |
| `TRANSLATION_GLOSSARY_SAMPLE_SIZE` | 3000 | Characters per sample chapter |

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
    ├── formatted/
    │   └── book.html       # Assembled HTML
    └── output/
        └── book.azw3       # Exported ebook
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
