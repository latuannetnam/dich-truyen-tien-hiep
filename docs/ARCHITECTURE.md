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

**Key files:**
- `crawler/pattern.py` - `PatternDiscovery` class uses LLM to find CSS selectors
- `crawler/downloader.py` - `ChapterDownloader` handles downloading with resume support
- `crawler/base.py` - HTTP client with retry logic and encoding auto-detection

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
│  │ - examples  │    │ - export  │    │ - chunk context  │  │
│  └─────────────┘    └───────────┘    └──────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Chunk-Based Translation (Parallel)

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

```python
# 1. Create chunks with context from previous chunk (Chinese source)
chunks_with_context = create_chunks_with_context(content)
# Each chunk has: {"main_text": "...", "context_text": "last 300 chars of prev"}

# 2. Translate all chunks in parallel (limited by semaphore)
semaphore = asyncio.Semaphore(config.concurrent_requests)  # default: 3

async def translate_with_limit(chunk_data, index):
    async with semaphore:
        return await translate_chunk(chunk_data["main_text"], 
                                      context=chunk_data["context_text"])

results = await asyncio.gather(*[translate_with_limit(c, i) for i, c in enumerate(chunks)])

# 3. Sort by index and combine
results.sort(key=lambda x: x[0])
final_text = "\n\n".join(results)
```

**Key design decisions:**
- Context uses **source Chinese** text (not translated output) to enable parallel processing
- Each chunk receives ~300 chars from previous chunk for narrative continuity
- Semaphore limits concurrent API calls to respect rate limits
- Results sorted by index to maintain correct order

### Style Template System

Style templates define translation behavior:

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

**Priority order when loading styles:**
1. Custom styles in `styles/` directory (checked first)
2. Built-in styles (fallback)

This allows users to override built-in styles by creating a YAML file with the same name.

### Style Generation Mechanism

The `style generate` command creates custom styles using LLM:

1. **Input**: User provides a Vietnamese description (e.g., "Văn phong ngôn tình, lãng mạn")
2. **Prompt Construction**: System prompts LLM to generate a JSON structure containing:
   - `guidelines`: 5-7 specific translation rules
   - `vocabulary`: 10-15 key term mappings
   - `examples`: 3-4 sample translations
   - `tone`: archaic/formal/casual
3. **YAML Serialization**: Validates JSON via Pydantic model and saves as YAML file in `styles/`

### Glossary Auto-Generation

```
┌──────────────────────────────────────────────────────────┐
│              Glossary Generation Pipeline                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. Random Sample Selection                               │
│     TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS=5               │
│     Select 5 random chapters from available chapters     │
│                                                           │
│  2. Extract Sample Content                                │
│     TRANSLATION_GLOSSARY_SAMPLE_SIZE=3000                │
│     Take first 3000 chars from each sample               │
│                                                           │
│  3. LLM Analysis                                          │
│     Send samples to LLM with structured prompt           │
│     Request MIN_ENTRIES to MAX_ENTRIES terms             │
│                                                           │
│  4. Parse & Save                                          │
│     Parse JSON response                                   │
│     Save to glossary.csv                                  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

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
│                                         │
│ Glossary:                               │
│ - 陈平安 → Trần Bình An                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│            USER PROMPT                  │
├─────────────────────────────────────────┤
│ Context (from previous chunk):          │
│ "...last 500 chars of previous..."      │
│                                         │
│ Text to translate:                      │
│ [current chunk content]                 │
└─────────────────────────────────────────┘
```

## Phase 3: Formatting

### HTML Assembly

```python
class HTMLAssembler:
    def assemble(self):
        # 1. Load book metadata
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

### Metadata Handling

Book metadata (title, author) is automatically translated during the translation phase:

```python
# In setup_translation()
if not progress.title_vi:
    progress.title_vi = await llm.translate_title(progress.title, "book")
    progress.author_vi = await llm.translate_title(progress.author, "author")
```

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
            # ... other options
        ]
        
        # 2. Execute conversion
        result = subprocess.run(cmd)
        
        # 3. Return result path
        return output_path
```

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

Both crawling and translation support resuming:

```python
# Resume mode (default): skip completed
if resume:
    chapters_to_process = [c for c in chapters if c.status == PENDING]

# Force mode: process all
if force:
    chapters_to_process = all_chapters
```

## Progress Display

### Chunk-Level Progress Bar with Parallel Indicator

```
Ch.1: 第一章 惊蛰... translating [1,2,3] [0/6] ━━━━━━━━━━━━━━━━   0%
                              ↑
                     Shows which chunks are currently being translated in parallel!

Ch.1: 第一章 惊蛰... [3/6] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  50%
```

The progress bar:
1. Pre-calculates total chunks across all chapters
2. Shows active parallel chunks (e.g., `translating [1,2,3]`)
3. Advances by 1 after each chunk completes
3. Shows current chapter, chunk index, and overall percentage

## Configuration System

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
| `OPENAI_` | LLM API configuration |
| `CRAWLER_` | HTTP client settings |
| `TRANSLATION_` | Translation & glossary settings |
| `CALIBRE_` | Ebook converter path |

#### Key Translation Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRANSLATION_CHUNK_SIZE` | 2000 | Characters per translation chunk |
| `TRANSLATION_CHUNK_OVERLAP` | 300 | Context chars from previous chunk (for parallel mode) |
| `TRANSLATION_CONCURRENT_REQUESTS` | 3 | Max parallel API calls |
| `TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS` | 5 | Chapters to sample for glossary generation |

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

## Error Handling

### Retry Logic

All network operations use exponential backoff:

```python
for attempt in range(max_retries):
    try:
        response = await client.get(url)
        return response
    except Exception:
        await sleep(delay * (2 ** attempt))
```

### Graceful Degradation

- Content extraction: falls back to body if selector fails
- Encoding detection: uses chardet if specified encoding fails
- Glossary parsing: returns empty list if LLM response invalid
