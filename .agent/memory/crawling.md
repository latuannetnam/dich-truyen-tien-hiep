---
description: Crawler internals, LLM pattern discovery, encoding, and resume logic
---

# Crawling

## Key Files

| File | Purpose |
|------|---------|
| `crawler/pattern.py` | LLM-powered CSS selector discovery |
| `crawler/downloader.py` | Chapter download with resume support |
| `crawler/base.py` | HTTP client, retry, encoding detection |

## LLM-Powered Pattern Discovery

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
│ - encoding               │
│ - has_pagination         │
└──────────────────────────┘
      │
      ▼ (for each chapter)
Chapter Page HTML ──▶ Extract content ──▶ Save as .txt
```

## Content Extraction & Fallback

```python
# Primary: use discovered selector
content = soup.select_one(patterns.content_selector)

# Fallback: extract from body if selector yields < 100 chars
if len(content) < 100:
    content = soup.find("body")
    # Filter navigation patterns (上一章, 下一章, etc.)
```

## Resume Logic

- Progress saved to `book.json` after each chapter
- On resume: skip chapters where `status == CRAWLED` or `status == TRANSLATED`
- Force mode (`--force`): re-crawl all chapters

## Encoding Detection

- Specified encoding tried first
- Falls back to `chardet` auto-detection if content is garbled
