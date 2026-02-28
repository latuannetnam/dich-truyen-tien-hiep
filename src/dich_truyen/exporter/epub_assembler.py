"""Direct EPUB assembly with parallel chapter generation.

This module provides fast EPUB creation by:
1. Writing chapter files in parallel using ThreadPoolExecutor
2. Generating EPUB structure directly (no Calibre dependency for EPUB)
3. Only using Calibre for conversion to AZW3/MOBI/PDF
"""

import asyncio
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

import structlog

from dich_truyen.config import ExportConfig, get_config
from dich_truyen.utils.progress import BookProgress, Chapter

logger = structlog.get_logger()


# EPUB templates
CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

STYLES_CSS = """
body {
    font-family: serif;
    line-height: 1.6;
    margin: 1em;
}

h1 {
    font-size: 1.8em;
    text-align: center;
    margin-bottom: 1em;
}

h2.chapter-title {
    font-size: 1.4em;
    text-align: center;
    margin: 2em 0 1em 0;
    page-break-before: always;
}

h2.chapter-title:first-of-type {
    page-break-before: avoid;
}

p {
    text-indent: 2em;
    margin: 0.5em 0;
}

.title-page {
    text-align: center;
    margin-top: 30%;
}

.title-page h1 {
    font-size: 2em;
    margin-bottom: 0.5em;
}

.title-page .author {
    font-size: 1.2em;
    font-style: italic;
}
"""


class DirectEPUBAssembler:
    """Fast EPUB assembly with parallel chapter generation."""

    def __init__(self, config: Optional[ExportConfig] = None):
        """Initialize assembler.
        
        Args:
            config: Export configuration (uses default if not provided)
        """
        self.config = config or get_config().export

    async def assemble(
        self,
        book_dir: Path,
        progress: Optional[BookProgress] = None,
    ) -> Path:
        """Assemble book into EPUB using parallel chapter writing.
        
        Args:
            book_dir: Book directory containing translated chapters
            progress: Book progress with chapter list
            
        Returns:
            Path to generated EPUB file
        """
        book_dir = Path(book_dir)
        
        # Load progress if not provided
        if not progress:
            progress = BookProgress.load(book_dir)
            if not progress:
                raise ValueError(f"No book.json found in {book_dir}")
        
        # Prepare directories
        epub_work_dir = book_dir / "epub_build"
        oebps_dir = epub_work_dir / "OEBPS"
        chapters_dir = oebps_dir / "chapters"
        meta_inf_dir = epub_work_dir / "META-INF"
        
        # Clean and create directories
        if epub_work_dir.exists():
            import shutil
            shutil.rmtree(epub_work_dir)
        
        chapters_dir.mkdir(parents=True, exist_ok=True)
        meta_inf_dir.mkdir(parents=True, exist_ok=True)
        
        # Get translated chapters
        translated_dir = book_dir / "translated"
        translated_chapters = self._get_translated_chapters(progress, translated_dir)
        
        if not translated_chapters:
            raise ValueError(f"No translated chapters found in {translated_dir}")
        
        logger.info("assembling_epub", chapters=len(translated_chapters))

        # Parallel chapter file writing
        completed = 0
        lock = asyncio.Lock()
        loop = asyncio.get_event_loop()

        async def write_with_progress(index: int, chapter: Chapter, content: str):
            nonlocal completed
            await loop.run_in_executor(
                None,
                self._write_chapter_file,
                chapters_dir,
                index,
                chapter,
                content,
            )
            async with lock:
                completed += 1

        # Create tasks for parallel execution
        with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            loop = asyncio.get_event_loop()
            tasks = []

            for i, (chapter, content) in enumerate(translated_chapters, 1):
                tasks.append(write_with_progress(i, chapter, content))

            await asyncio.gather(*tasks)

        logger.debug("epub_chapters_written", count=len(translated_chapters))

        # Generate manifest
        chapters_only = [ch for ch, _ in translated_chapters]
        self._write_manifest(oebps_dir, progress, chapters_only)

        # Generate TOC
        self._write_toc(oebps_dir, progress, chapters_only)

        # Write static files
        self._write_container(meta_inf_dir)
        self._write_styles(oebps_dir)
        self._write_title_page(oebps_dir, progress)

        # Create ZIP
        output_dir = book_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        epub_path = output_dir / "book.epub"

        self._create_epub_zip(epub_work_dir, epub_path)

        logger.info("epub_created", path=str(epub_path))
        return epub_path

    def _get_translated_chapters(
        self,
        progress: BookProgress,
        translated_dir: Path,
    ) -> list[tuple[Chapter, str]]:
        """Load translated chapter content.
        
        Returns:
            List of (Chapter, content) tuples
        """
        result = []
        for chapter in progress.chapters:
            txt_path = translated_dir / f"{chapter.index}.txt"
            if txt_path.exists():
                content = txt_path.read_text(encoding="utf-8")
                result.append((chapter, content))
        return result

    def _write_chapter_file(
        self,
        chapters_dir: Path,
        index: int,
        chapter: Chapter,
        content: str,
    ) -> None:
        """Write single chapter as XHTML file."""
        title = escape(chapter.title_vi or chapter.title_cn or f"Chương {index}")
        
        # Convert paragraphs to HTML
        paragraphs = content.strip().split("\n\n")
        html_paragraphs = "\n".join(
            f"    <p>{escape(p.strip())}</p>" for p in paragraphs if p.strip()
        )
        
        xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="vi">
<head>
    <meta charset="UTF-8"/>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="../styles.css"/>
</head>
<body>
    <h2 class="chapter-title">{title}</h2>
{html_paragraphs}
</body>
</html>"""
        
        path = chapters_dir / f"chapter_{index:04d}.xhtml"
        path.write_text(xhtml, encoding="utf-8")

    def _write_manifest(
        self,
        oebps_dir: Path,
        progress: BookProgress,
        chapters: list[Chapter],
    ) -> None:
        """Generate content.opf manifest file."""
        title = escape(progress.title_vi or progress.title or "Untitled")
        author = escape(progress.author_vi or progress.author or "Unknown")
        
        # Build manifest items
        manifest_items = ['    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>']
        manifest_items.append('    <item id="styles" href="styles.css" media-type="text/css"/>')
        manifest_items.append('    <item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>')
        
        for i, _ in enumerate(chapters, 1):
            manifest_items.append(
                f'    <item id="chapter{i:04d}" href="chapters/chapter_{i:04d}.xhtml" media-type="application/xhtml+xml"/>'
            )
        
        # Build spine
        spine_items = ['    <itemref idref="titlepage"/>']
        for i, _ in enumerate(chapters, 1):
            spine_items.append(f'    <itemref idref="chapter{i:04d}"/>')
        
        opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{title}</dc:title>
    <dc:creator opf:role="aut">{author}</dc:creator>
    <dc:language>vi</dc:language>
    <dc:identifier id="BookId">urn:uuid:dich-truyen-{hash(title) % 1000000}</dc:identifier>
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx">
{chr(10).join(spine_items)}
  </spine>
</package>"""
        
        path = oebps_dir / "content.opf"
        path.write_text(opf, encoding="utf-8")

    def _write_toc(
        self,
        oebps_dir: Path,
        progress: BookProgress,
        chapters: list[Chapter],
    ) -> None:
        """Generate toc.ncx navigation file."""
        title = escape(progress.title_vi or progress.title or "Untitled")
        
        # Build navPoints
        nav_points = []
        for i, chapter in enumerate(chapters, 1):
            ch_title = escape(chapter.title_vi or chapter.title_cn or f"Chương {i}")
            nav_points.append(f"""    <navPoint id="navpoint{i}" playOrder="{i}">
      <navLabel><text>{ch_title}</text></navLabel>
      <content src="chapters/chapter_{i:04d}.xhtml"/>
    </navPoint>""")
        
        ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:dich-truyen-{hash(title) % 1000000}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
{chr(10).join(nav_points)}
  </navMap>
</ncx>"""
        
        path = oebps_dir / "toc.ncx"
        path.write_text(ncx, encoding="utf-8")

    def _write_container(self, meta_inf_dir: Path) -> None:
        """Write META-INF/container.xml."""
        path = meta_inf_dir / "container.xml"
        path.write_text(CONTAINER_XML, encoding="utf-8")

    def _write_styles(self, oebps_dir: Path) -> None:
        """Write CSS stylesheet."""
        path = oebps_dir / "styles.css"
        path.write_text(STYLES_CSS, encoding="utf-8")

    def _write_title_page(self, oebps_dir: Path, progress: BookProgress) -> None:
        """Write title page XHTML."""
        title = escape(progress.title_vi or progress.title or "Untitled")
        author = escape(progress.author_vi or progress.author or "Unknown")
        
        xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="vi">
<head>
    <meta charset="UTF-8"/>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <div class="title-page">
        <h1>{title}</h1>
        <p class="author">{author}</p>
    </div>
</body>
</html>"""
        
        path = oebps_dir / "titlepage.xhtml"
        path.write_text(xhtml, encoding="utf-8")

    def _create_epub_zip(self, work_dir: Path, output_path: Path) -> None:
        """Create EPUB ZIP archive.
        
        EPUB spec requires:
        1. mimetype file must be first entry
        2. mimetype must be uncompressed (ZIP_STORED)
        """
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # mimetype MUST be first and uncompressed
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            
            # Add all other files
            for file_path in sorted(work_dir.rglob("*")):
                if file_path.is_file():
                    arcname = file_path.relative_to(work_dir)
                    zf.write(file_path, arcname)


async def assemble_book_fast(
    book_dir: Path,
    progress: Optional[BookProgress] = None,
) -> Path:
    """Convenience function for fast EPUB assembly.
    
    Args:
        book_dir: Book directory
        progress: Optional book progress
        
    Returns:
        Path to generated EPUB
    """
    assembler = DirectEPUBAssembler()
    return await assembler.assemble(book_dir, progress)
