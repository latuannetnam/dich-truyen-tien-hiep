---
description: EPUB assembly, Calibre integration, output formats, and file structure
---

# Export

## Key Files

| File | Purpose |
|------|---------|
| `exporter/epub_assembler.py` | Direct EPUB assembly with parallel writing |
| `exporter/calibre.py` | Calibre integration for AZW3/MOBI/PDF |
| `services/export_service.py` | Service wrapper for API routes |

## Export Flow

```
Translated Chapters (/translated/*.txt)
              │
              ▼ (parallel file writing, 8 threads)
      DirectEPUBAssembler
      ├── chapter_0001.xhtml
      ├── chapter_0002.xhtml  → OEBPS/chapters/
      └── ...
      Generate: content.opf, toc.ncx, styles.css, titlepage.xhtml
      ZIP → book.epub
              │
              ▼ (if format ≠ epub)
      Calibre: EPUB → AZW3 / MOBI / PDF
```

## EPUB Directory Structure

```
epub_build/
├── mimetype
├── META-INF/container.xml
└── OEBPS/
    ├── content.opf        # Manifest + spine
    ├── toc.ncx            # Navigation
    ├── styles.css
    ├── titlepage.xhtml
    └── chapters/
        ├── chapter_0001.xhtml
        └── ...
```

## Parallel Assembly Pattern

```python
class DirectEPUBAssembler:
    async def assemble(self, book_dir, chapters):
        with ThreadPoolExecutor(max_workers=8) as executor:
            tasks = [
                loop.run_in_executor(executor, self._write_chapter_file, ...)
                for index, chapter in enumerate(chapters, 1)
            ]
            await asyncio.gather(*tasks)
        self._write_manifest(...)
        self._write_toc(...)
        self._create_epub_zip(...)
```

## Supported Output Formats

| Format | Method |
|--------|--------|
| EPUB | Direct assembly (no Calibre needed) |
| AZW3 | Calibre: EPUB → AZW3 |
| MOBI | Calibre: EPUB → MOBI |
| PDF | Calibre: EPUB → PDF |

## Key Env Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `EXPORT_PARALLEL_WORKERS` | 8 | Threads for chapter file writing |
| `EXPORT_VOLUME_SIZE` | 0 | Chapters per volume (0 = single file) |
| `EXPORT_FAST_MODE` | true | Use direct EPUB assembly |
| `CALIBRE_EXECUTABLE` | `ebook-convert` | Path to Calibre converter |

## ExportService API

```python
from dich_truyen.services.export_service import ExportService

svc = ExportService(books_dir)
formats = svc.get_supported_formats()            # ["epub", "azw3", "mobi", "pdf"]
status = svc.get_export_status("book-id")         # {"formats": {"epub": "/path/to/file"}}
result = await svc.export("book-id", "epub")      # Wraps export_book()
```
