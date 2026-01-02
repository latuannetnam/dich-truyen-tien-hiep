# Dịch Truyện - Chinese Novel Translation Tool

A command-line tool for crawling, translating, and exporting Chinese novels to Vietnamese ebooks.

## Features

- 🕷️ **Smart Web Crawler**: Uses LLM to discover chapter structure from Chinese novel websites
- 🌐 **Translation Engine**: Translates Chinese to Vietnamese with customizable style templates
- 📖 **4 Built-in Styles**: Tiên hiệp, Kiếm hiệp, Huyền huyễn, Đô thị
- 📚 **Glossary System**: Maintains consistent term translations (CSV import/export)
- 📕 **Ebook Export**: Converts to EPUB, AZW3, MOBI, PDF via Calibre
- 🔄 **Resumable Operations**: Continue interrupted downloads/translations

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/dich-truyen-tien-hiep.git
cd dich-truyen-tien-hiep

# Install with uv
uv sync

# Install Playwright for JavaScript-rendered sites (optional)
uv run playwright install chromium
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required settings:
```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1  # or compatible endpoint
OPENAI_MODEL=gpt-4o
```

## Quick Start

### Full Pipeline

```bash
uv run dich-truyen pipeline \
  --url "https://www.piaotia.com/html/8/8717/index.html" \
  --style tien_hiep \
  --format epub \
  --chapters 1-10
```

### Phase by Phase

```bash
# Phase 1: Crawl chapters
uv run dich-truyen crawl --url "https://www.piaotia.com/html/8/8717/index.html"

# Phase 2: Translate
uv run dich-truyen translate --book-dir books/html-8-8717 --style tien_hiep

# Phase 3: Format to HTML
uv run dich-truyen format --book-dir books/html-8-8717 --translator "AI"

# Phase 4: Export to EPUB
uv run dich-truyen export --book-dir books/html-8-8717 --format epub
```

## Command Reference

### `crawl` - Download chapters from website

```bash
uv run dich-truyen crawl [OPTIONS]

Options:
  --url TEXT          Book index page URL (required)
  --book-dir PATH     Book directory
  --chapters TEXT     Chapter range, e.g., "1-100" or "1,5,10-20"
  --encoding TEXT     Force encoding (auto-detect if not set)
  --resume/--no-resume  Resume interrupted download (default: resume)
```

### `translate` - Translate chapters

```bash
uv run dich-truyen translate [OPTIONS]

Options:
  --book-dir PATH     Book directory (required)
  --style TEXT        Style template (default: tien_hiep)
  --glossary PATH     Import glossary from CSV
  --auto-glossary/--no-auto-glossary  Auto-generate glossary (default: on)
  --chunk-size INT    Characters per translation chunk
  --resume/--no-resume  Resume interrupted translation
```

### `format` - Assemble HTML book

```bash
uv run dich-truyen format [OPTIONS]

Options:
  --book-dir PATH     Book directory (required)
  --title TEXT        Override book title
  --author TEXT       Override author name
  --translator TEXT   Translator name
  --cover PATH        Cover image path
```

### `export` - Convert to ebook

```bash
uv run dich-truyen export [OPTIONS]

Options:
  --book-dir PATH     Book directory (required)
  --format CHOICE     Output format: epub, azw3, mobi, pdf (default: epub)
  --calibre-path PATH Path to ebook-convert executable
```

### Glossary Management

```bash
# Export glossary
uv run dich-truyen glossary export --book-dir ./books/my-book -o glossary.csv

# Import glossary
uv run dich-truyen glossary import --book-dir ./books/my-book -i edited_glossary.csv
```

### Style Templates

```bash
# List available styles
uv run dich-truyen style list

# Generate custom style
uv run dich-truyen style generate \
  --description "Văn phong nhẹ nhàng, hiện đại" \
  -o styles/custom.yaml
```

## Available Styles

| Style | Description | Use For |
|-------|-------------|---------|
| `tien_hiep` | Tiên hiệp, tu chân, cổ trang | 仙侠, 修真 novels |
| `kiem_hiep` | Kiếm hiệp, võ lâm, giang hồ | 武侠 novels |
| `huyen_huyen` | Huyền huyễn, kỳ ảo, ma pháp | 玄幻 novels |
| `do_thi` | Đô thị, hiện đại, nhẹ nhàng | 都市 novels |

## Book Directory Structure

```
books/
└── html-8-8717/            # Book folder
    ├── book.json           # Book metadata & progress
    ├── glossary.csv        # Term translations
    ├── raw/                # Downloaded chapters
    │   ├── 0001_chapter.txt
    │   └── ...
    ├── translated/         # Translated chapters
    │   └── ...
    ├── formatted/          # Assembled HTML
    │   └── book.html
    └── output/             # Exported ebooks
        └── book.epub
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Calibre](https://calibre-ebook.com/) (for ebook export)
- OpenAI API key (or compatible endpoint)

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/dich_truyen --cov-report=html
```

## License

MIT License
