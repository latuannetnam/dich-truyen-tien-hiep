---
description: CLI commands, options, and how to add new commands
---

# CLI

## Key File

`cli.py` — all commands defined with `@cli.command()` using Click.

## Command Tree

```
dich-truyen
├── pipeline           Main workflow: crawl + translate + (export)
│   ├── URL            Source novel URL (required)
│   ├── --crawl-only   Only crawl, skip translation
│   ├── --translate-only  Only translate already-crawled chapters
│   ├── --skip-export  Don't export after translation
│   ├── --force        Re-process already completed chapters
│   ├── --start N      Start from chapter N
│   └── --end N        Stop at chapter N
│
├── export             Standalone ebook export
│   ├── BOOK_DIR       Path to book directory
│   └── --format       epub | azw3 | mobi | pdf
│
├── glossary           Manage the glossary
│   ├── show           Print glossary to console
│   ├── export PATH    Export glossary.csv to PATH
│   └── import PATH    Import from PATH into glossary.csv
│
└── style              Manage translation styles
    ├── list           List available styles (built-in + custom)
    └── generate NAME  Generate a new style YAML template
│
└── ui                 Launch web UI server
    ├── --port N       API server port (default: 8000)
    ├── --host ADDR    API server host (default: 127.0.0.1)
    └── --no-browser   Don't auto-open browser
```

## How to Add a New Command

```python
@cli.command()
@click.argument("my_arg")
@click.option("--my-option", default="value", help="Description")
def my_command(my_arg: str, my_option: str) -> None:
    """Short description shown in --help."""
    config = get_config()
    # implementation
```

## Running

```bash
uv run dich-truyen [command] [options]

# Examples
uv run dich-truyen pipeline "https://site.com/novel"
uv run dich-truyen export books/my-book --format azw3
uv run dich-truyen glossary show
uv run dich-truyen ui --port 8000 --no-browser
```
