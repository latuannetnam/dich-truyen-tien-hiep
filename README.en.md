# Dịch Truyện - Chinese Novel Translation Tool

> **Language:** [English](README.en.md) | [Tiếng Việt](README.md)

A command-line tool for crawling, translating, and exporting Chinese novels to Vietnamese ebooks.

## Features

### Core Features

- 🕷️ **Smart Crawler**: Uses LLM to automatically discover chapter structure from Chinese novel websites
- 🌐 **Translation Engine**: Translates Chinese to Vietnamese with customizable style templates
- 📖 **4 Built-in Styles**: Tiên hiệp, Kiếm hiệp, Huyền huyễn, Đô thị
- 📚 **Glossary System**: Maintains consistent terminology (import/export CSV)
- 📕 **Ebook Export**: Convert to EPUB, AZW3, MOBI, PDF via Calibre
- 🔄 **Resumable Operations**: Continue interrupted downloads/translations
- ⚡ **Streaming Pipeline**: Concurrent crawl and translate with multiple workers

### Advanced Techniques

| Technique | Description |
|-----------|-------------|
| 🎯 **Smart Dialogue Chunking** | Keeps dialogue blocks together to maintain context |
| 📈 **Progressive Glossary Building** | Automatically extracts new terms from each translated chapter |
| 🔍 **TF-IDF Glossary Selection** | Selects most relevant glossary terms based on TF-IDF scores |
| ⚡ **Direct EPUB Assembly** | Creates EPUB directly with parallel file writing, 10-20x faster |
| 🚀 **Concurrent Pipeline** | Crawl and translate in parallel with multiple workers |

## Installation

```bash
# Clone the repository
git clone https://github.com/latuannetnam/dich-truyen-tien-hiep.git
cd dich-truyen-tien-hiep

# Install with uv
uv sync
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required settings:
```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1
```

## Quick Start

### Full Pipeline (Simplest)

```bash
# Crawl + translate + export to EPUB
uv run dich-truyen pipeline --url "https://www.piaotia.com/html/8/8717/index.html"

# Only first 10 chapters, export to Kindle format
uv run dich-truyen pipeline \
  --url "https://www.piaotia.com/html/8/8717/index.html" \
  --chapters 1-10 \
  --format azw3
```

### Pipeline Modes

#### Crawl Only (Review Before Translation)

```bash
# Crawl chapters for review before translating
uv run dich-truyen pipeline --url "https://..." --crawl-only

# Check downloaded chapters in books/<book-dir>/raw/
```

#### Translate Only (Existing Book)

```bash
# Translate a previously crawled book
uv run dich-truyen pipeline --book-dir books/my-book --translate-only

# Translate with custom glossary
uv run dich-truyen pipeline \
  --book-dir books/my-book \
  --translate-only \
  --glossary my-glossary.csv
```

#### Resume Interrupted Work

```bash
# Resume from where you left off (auto-detected)
uv run dich-truyen pipeline --book-dir books/my-book

# Force restart from beginning
uv run dich-truyen pipeline --book-dir books/my-book --force
```

## Command Reference

### `pipeline` - Main Command

```bash
uv run dich-truyen pipeline [OPTIONS]

Options:
  --url TEXT            Book index page URL (for new books)
  --book-dir PATH       Existing book directory
  --chapters TEXT       Chapter range, e.g., "1-100"
  --style TEXT          Translation style (default: tien_hiep)
  --format CHOICE       Output format: epub, azw3, mobi, pdf
  --workers INT         Number of translation workers (default: 3)
  --crawl-only          Stop after crawl phase (no translation)
  --translate-only      Skip crawl, only translate existing chapters
  --skip-export         Skip export phase
  --no-glossary         Disable auto-glossary generation
  --glossary PATH       Import glossary from CSV before translation
  --force               Force re-process all chapters
```

### `export` - Export to Ebook

```bash
uv run dich-truyen export --book-dir books/my-book --format azw3
```

### `glossary` - Manage Glossaries

```bash
# Show glossary
uv run dich-truyen glossary show --book-dir books/my-book

# Export glossary
uv run dich-truyen glossary export --book-dir books/my-book -o glossary.csv

# Import glossary (merge with existing)
uv run dich-truyen glossary import --book-dir books/my-book -i edited.csv --merge

# Import glossary (replace)
uv run dich-truyen glossary import --book-dir books/my-book -i new.csv --replace
```

### `style` - Manage Styles

```bash
# List styles
uv run dich-truyen style list

# Generate new style using LLM
uv run dich-truyen style generate \
  --description "Modern romance style, soft and emotional" \
  -o styles/romance.yaml
```

## Translation Styles

### Built-in Styles (Default: `tien_hiep`)

| Style | Description | Use For |
|-------|-------------|---------|
| `tien_hiep` | Xianxia, cultivation, ancient setting | 仙侠, 修真 novels |
| `kiem_hiep` | Wuxia, martial arts, jianghu | 武侠 novels |
| `huyen_huyen` | Xuanhuan, fantasy, magic | 玄幻 novels |
| `do_thi` | Urban, modern, casual | 都市 novels |

### Custom Styles

```yaml
# styles/romance.yaml
name: romance
description: Modern romance style
guidelines:
  - Soft and emotional language
  - Pronouns: 'anh', 'em'
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
└── 8717-indexhtml/
    ├── book.json           # Metadata & progress
    ├── glossary.csv        # Translation glossary
    ├── raw/                # Downloaded chapters
    ├── translated/         # Translated chapters
    ├── epub_build/         # EPUB build directory
    └── output/             # Exported ebooks
        ├── book.epub
        └── book.azw3
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
