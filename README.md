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
git clone https://github.com/latuannetnam/dich-truyen-tien-hiep.git
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
OPENAI_MODEL=gpt-4.1
```

## Quick Start

### Full Pipeline (Simplest)

Process an entire book in one command:

```bash
# Default: crawl all chapters, translate, format, export to EPUB
uv run dich-truyen pipeline --url "https://www.piaotia.com/html/8/8717/index.html"

# Translate first 10 chapters only, export to Kindle format
uv run dich-truyen pipeline \
  --url "https://www.piaotia.com/html/8/8717/index.html" \
  --chapters 1-10 \
  --format azw3

# Use custom style and force re-process
uv run dich-truyen pipeline \
  --url "https://example.com/novel/index.html" \
  --style kiem_hiep \
  --chapters 1-50 \
  --format pdf \
  --force
```

### Individual Commands (More Control)

#### Use Case 1: Download only (no translation yet)

```bash
# Just crawl chapters 1-100 for later translation
uv run dich-truyen crawl \
  --url "https://www.piaotia.com/html/8/8717/index.html" \
  --chapters 1-100

# Crawl with forced encoding for problematic sites
uv run dich-truyen crawl \
  --url "https://example.com/novel/" \
  --encoding gbk
```

#### Use Case 2: Translate specific chapters

```bash
# Translate chapters 1-10 with default style
uv run dich-truyen translate \
  --book-dir books/8717-indexhtml \
  --chapters 1-10

# Translate with custom glossary (expert mode)
uv run dich-truyen translate \
  --book-dir books/8717-indexhtml \
  --glossary my-custom-glossary.csv \
  --style huyen_huyen \
  --no-auto-glossary

# Force re-translate chapters with different style
uv run dich-truyen translate \
  --book-dir books/8717-indexhtml \
  --chapters 1-5 \
  --style kiem_hiep \
  --force
```

#### Use Case 3: Custom book metadata

```bash
# Format with custom title and translator name
uv run dich-truyen format \
  --book-dir books/8717-indexhtml \
  --title "Kiếm Lai" \
  --author "Phong Hỏa Hí Chư Hầu" \
  --translator "AI Translator" \
  --cover cover.jpg
```

#### Use Case 4: Export to different formats

```bash
# Export to Kindle (AZW3)
uv run dich-truyen export --book-dir books/8717-indexhtml --format azw3

# Export to PDF for printing
uv run dich-truyen export --book-dir books/8717-indexhtml --format pdf

# Export with custom Calibre path
uv run dich-truyen export \
  --book-dir books/8717-indexhtml \
  --format epub \
  --calibre-path "C:/Program Files/Calibre2/ebook-convert.exe"
```

#### Use Case 5: Resume interrupted work

```bash
# Continue downloading where you left off
uv run dich-truyen crawl --url "https://..." --resume

# Continue translating (default behavior)
uv run dich-truyen translate --book-dir books/8717-indexhtml
```

## Command Reference

### `crawl` - Download chapters from website

```bash
uv run dich-truyen crawl [OPTIONS]

Options:
  --url TEXT            Book index page URL (required)
  --book-dir PATH       Book directory
  --chapters TEXT       Chapter range, e.g., "1-100" or "1,5,10-20"
  --encoding TEXT       Force encoding (auto-detect if not set)
  --resume/--no-resume  Resume interrupted download (default: resume)
  --force               Force re-download even if already downloaded
```

### `translate` - Translate chapters

```bash
uv run dich-truyen translate [OPTIONS]

Options:
  --book-dir PATH       Book directory (required)
  --chapters TEXT       Chapter range, e.g., "1-100" or "1,5,10-20"
  --style TEXT          Style template (default: tien_hiep)
  --glossary PATH       Import glossary from CSV
  --auto-glossary       Auto-generate glossary (default: on)
  --chunk-size INT      Characters per translation chunk
  --resume/--no-resume  Resume interrupted translation
  --force               Force re-translate even if already translated
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

#### List Available Styles

```bash
uv run dich-truyen style list
```

#### Generate Custom Style

```bash
# Create a new custom style using LLM
uv run dich-truyen style generate \
  --description "Văn phong ngôn tình, lãng mạn hiện đại" \
  -o styles/ngon_tinh.yaml
```

## Translation Styles

### Built-in Styles (Default: `tien_hiep`)

| Style | Description | Use For |
|-------|-------------|---------|
| `tien_hiep` | Tiên hiệp, tu chân, cổ trang | 仙侠, 修真 novels |
| `kiem_hiep` | Kiếm hiệp, võ lâm, giang hồ | 武侠 novels |
| `huyen_huyen` | Huyền huyễn, kỳ ảo, ma pháp | 玄幻 novels |
| `do_thi` | Đô thị, hiện đại, nhẹ nhàng | 都市 novels |

### Custom Styles

You can create custom styles or **override built-in styles** by placing YAML files in the `styles/` directory.

**Priority order:**
1. Custom styles in `styles/` (checked first)
2. Built-in styles (fallback)

**Examples:**

```bash
# Use a built-in style
uv run dich-truyen translate --book-dir books/my-book --style tien_hiep

# Use a custom style
uv run dich-truyen translate --book-dir books/my-book --style ngon_tinh

# Override a built-in style: create styles/tien_hiep.yaml
# Your custom styles/tien_hiep.yaml will be used instead of the built-in one
uv run dich-truyen style generate \
  --description "Văn phong tiên hiệp cải tiến" \
  -o styles/tien_hiep.yaml
```

**Custom style structure (YAML):**

```yaml
name: ngon_tinh
description: Văn phong ngôn tình, lãng mạn hiện đại
guidelines:
  - Ngôn ngữ mềm mại, lãng mạn
  - Đại từ: 'anh', 'em', 'cô ấy'
vocabulary:
  我: em
  你: anh
  爱: yêu
tone: casual
examples:
  - chinese: "我爱你"
    vietnamese: "Em yêu anh"
```

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
