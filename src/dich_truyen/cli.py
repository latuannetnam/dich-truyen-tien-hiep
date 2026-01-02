"""Main CLI entry point for dich-truyen."""

import asyncio
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console

from dich_truyen import __version__
from dich_truyen.config import AppConfig, set_config

console = Console()


def setup_config(env_file: Optional[Path] = None) -> None:
    """Load configuration from environment."""
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    config = AppConfig.load(env_file)
    set_config(config)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output")
@click.option("--env-file", type=click.Path(exists=True), help="Path to .env file")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, verbose: bool, quiet: bool, env_file: Optional[str]) -> None:
    """Chinese novel translation tool.

    Crawl, translate, format, and export Chinese novels to ebooks.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # Setup configuration
    setup_config(Path(env_file) if env_file else None)


# =============================================================================
# Crawl Command
# =============================================================================


@cli.command()
@click.option("--url", required=True, help="Book index page URL")
@click.option(
    "--book-dir",
    type=click.Path(),
    help="Book directory (auto-generated from URL if not specified)",
)
@click.option("--chapters", help="Chapter range (e.g., 1-100 or 1,5,10-20)")
@click.option("--encoding", help="Force encoding (auto-detect if not set)")
@click.option("--resume/--no-resume", default=True, help="Resume interrupted download")
@click.option("--force", is_flag=True, help="Force re-download even if already downloaded")
@click.pass_context
def crawl(
    ctx,
    url: str,
    book_dir: Optional[str],
    chapters: Optional[str],
    encoding: Optional[str],
    resume: bool,
    force: bool,
) -> None:
    """Phase 1: Crawl chapters from website.

    Downloads all chapters from a Chinese novel website.
    Uses LLM to automatically discover chapter list structure.
    """
    from dich_truyen.config import get_config
    from dich_truyen.crawler.downloader import ChapterDownloader, create_book_directory

    async def run():
        # Create or use specified book directory
        if book_dir:
            target_dir = Path(book_dir)
        else:
            target_dir = await create_book_directory(
                url, get_config().books_dir
            )

        console.print(f"[blue]Book directory: {target_dir}[/blue]")

        # Initialize downloader
        downloader = ChapterDownloader(target_dir)

        # Initialize book (discover patterns, extract chapter list)
        await downloader.initialize_book(url, encoding)

        # Download chapters (force disables resume)
        result = await downloader.download_chapters(chapters, resume=resume and not force)

        if result.failed > 0:
            console.print(f"[yellow]Warning: {result.failed} chapters failed[/yellow]")
            for error in result.errors[:5]:
                console.print(f"  - {error}")

    asyncio.run(run())


# =============================================================================
# Translate Command
# =============================================================================


@cli.command()
@click.option("--book-dir", required=True, type=click.Path(exists=True), help="Book directory")
@click.option("--style", default="tien_hiep", help="Translation style template")
@click.option("--chapters", help="Chapter range (e.g., 1-100 or 1,5,10-20)")
@click.option("--glossary", type=click.Path(exists=True), help="Import glossary CSV")
@click.option("--auto-glossary/--no-auto-glossary", default=True, help="Auto-generate glossary")
@click.option("--chunk-size", type=int, help="Characters per translation chunk")
@click.option("--resume/--no-resume", default=True, help="Resume interrupted translation")
@click.option("--force", is_flag=True, help="Force re-translate even if already translated")
@click.pass_context
def translate(
    ctx,
    book_dir: str,
    style: str,
    chapters: Optional[str],
    glossary: Optional[str],
    auto_glossary: bool,
    chunk_size: Optional[int],
    resume: bool,
    force: bool,
) -> None:
    """Phase 2: Translate chapters using LLM.

    Translates downloaded chapters from Chinese to Vietnamese.
    """
    from dich_truyen.translator.engine import TranslationEngine, setup_translation

    async def run():
        # Setup translation engine
        engine = await setup_translation(
            book_dir=Path(book_dir),
            style_name=style,
            glossary_path=Path(glossary) if glossary else None,
            auto_glossary=auto_glossary,
        )

        # Override chunk size if specified
        if chunk_size:
            engine.config.chunk_size = chunk_size

        # Run translation (force disables resume)
        result = await engine.translate_book(
            book_dir=Path(book_dir),
            chapters_spec=chapters,
            resume=resume and not force,
        )

        if result.failed > 0:
            console.print(f"[yellow]Warning: {result.failed} chapters failed[/yellow]")
            for error in result.errors[:5]:
                console.print(f"  - {error}")

    asyncio.run(run())


# =============================================================================
# Format Command
# =============================================================================


@cli.command("format")
@click.option("--book-dir", required=True, type=click.Path(exists=True), help="Book directory")
@click.option("--title", help="Override book title")
@click.option("--author", help="Override author name")
@click.option("--translator", help="Translator name")
@click.option("--cover", type=click.Path(exists=True), help="Cover image path")
@click.pass_context
def format_book(
    ctx,
    book_dir: str,
    title: Optional[str],
    author: Optional[str],
    translator: Optional[str],
    cover: Optional[str],
) -> None:
    """Phase 3: Format translated chapters into HTML.

    Assembles translated chapters into a single HTML file with TOC.
    """
    from dich_truyen.formatter.assembler import HTMLAssembler

    assembler = HTMLAssembler(Path(book_dir))

    # Handle cover image
    if cover:
        import shutil
        cover_path = Path(cover)
        dest_cover = Path(book_dir) / "cover" / cover_path.name
        dest_cover.parent.mkdir(exist_ok=True)
        shutil.copy(cover_path, dest_cover)
        assembler.load_book_data()
        assembler.metadata.cover_path = str(dest_cover)

    output_path = assembler.assemble(
        title=title,
        author=author,
        translator=translator,
    )

    console.print(f"[green]HTML book created: {output_path}[/green]")


# =============================================================================
# Export Command
# =============================================================================


@cli.command()
@click.option("--book-dir", required=True, type=click.Path(exists=True), help="Book directory")
@click.option(
    "--format",
    "output_format",
    default="azw3",
    type=click.Choice(["epub", "azw3", "mobi", "pdf"]),
    help="Output format",
)
@click.option("--calibre-path", help="Path to ebook-convert executable")
@click.pass_context
def export(
    ctx,
    book_dir: str,
    output_format: str,
    calibre_path: Optional[str],
) -> None:
    """Phase 4: Export to ebook format.

    Converts formatted HTML to ebook using Calibre.
    """
    from dich_truyen.exporter.calibre import export_book

    result = export_book(
        book_dir=Path(book_dir),
        output_format=output_format,
        calibre_path=calibre_path,
    )

    if not result.success:
        console.print(f"[red]Export failed: {result.error_message}[/red]")
        raise SystemExit(1)

    console.print(f"[green]Book exported: {result.output_path}[/green]")


# =============================================================================
# Pipeline Command
# =============================================================================


@cli.command()
@click.option("--url", required=True, help="Book index page URL")
@click.option("--style", default="tien_hiep", help="Translation style template")
@click.option(
    "--format",
    "output_format",
    default="azw3",
    type=click.Choice(["epub", "azw3", "mobi", "pdf"]),
    help="Output format",
)
@click.option("--chapters", help="Chapter range (e.g., 1-100)")
@click.option("--book-dir", type=click.Path(), help="Book directory")
@click.option("--force", is_flag=True, help="Force re-process all steps")
@click.pass_context
def pipeline(
    ctx,
    url: str,
    style: str,
    output_format: str,
    chapters: Optional[str],
    book_dir: Optional[str],
    force: bool,
) -> None:
    """Run full pipeline: crawl → translate → format → export.

    Complete end-to-end processing of a Chinese novel.
    """
    from dich_truyen.config import get_config
    from dich_truyen.crawler.downloader import ChapterDownloader, create_book_directory
    from dich_truyen.exporter.calibre import export_book
    from dich_truyen.formatter.assembler import HTMLAssembler
    from dich_truyen.translator.engine import setup_translation

    async def run():
        # Phase 1: Crawl
        console.print("\n[bold blue]═══ Phase 1: Crawling ═══[/bold blue]")
        
        if book_dir:
            target_dir = Path(book_dir)
        else:
            target_dir = await create_book_directory(url, get_config().books_dir)

        console.print(f"Book directory: {target_dir}")

        downloader = ChapterDownloader(target_dir)
        await downloader.initialize_book(url)
        crawl_result = await downloader.download_chapters(chapters, resume=not force)

        if crawl_result.failed > 0:
            console.print(f"[yellow]Warning: {crawl_result.failed} chapters failed to download[/yellow]")

        # Phase 2: Translate
        console.print("\n[bold blue]═══ Phase 2: Translating ═══[/bold blue]")
        
        engine = await setup_translation(
            book_dir=target_dir,
            style_name=style,
            auto_glossary=True,
        )

        translate_result = await engine.translate_book(
            book_dir=target_dir,
            chapters_spec=chapters,
            resume=not force,
        )

        if translate_result.failed > 0:
            console.print(f"[yellow]Warning: {translate_result.failed} chapters failed to translate[/yellow]")

        # Phase 3: Format
        console.print("\n[bold blue]═══ Phase 3: Formatting ═══[/bold blue]")
        
        assembler = HTMLAssembler(target_dir)
        html_path = assembler.assemble()

        # Phase 4: Export
        console.print("\n[bold blue]═══ Phase 4: Exporting ═══[/bold blue]")
        
        export_result = export_book(
            book_dir=target_dir,
            output_format=output_format,
        )

        if not export_result.success:
            console.print(f"[red]Export failed: {export_result.error_message}[/red]")
            raise SystemExit(1)

        # Summary
        console.print("\n[bold green]═══ Pipeline Complete! ═══[/bold green]")
        console.print(f"  Book: {target_dir}")
        console.print(f"  Chapters: {crawl_result.downloaded}")
        console.print(f"  Translated: {translate_result.translated}")
        console.print(f"  Output: {export_result.output_path}")

    asyncio.run(run())


# =============================================================================
# Glossary Commands
# =============================================================================


@cli.group()
def glossary():
    """Manage translation glossaries."""
    pass


@glossary.command("export")
@click.option("--book-dir", required=True, type=click.Path(exists=True), help="Book directory")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output CSV path")
def glossary_export(book_dir: str, output: str) -> None:
    """Export glossary to CSV file."""
    console.print("[yellow]Glossary export not yet implemented[/yellow]")


@glossary.command("import")
@click.option("--book-dir", required=True, type=click.Path(exists=True), help="Book directory")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True))
def glossary_import(book_dir: str, input_file: str) -> None:
    """Import glossary from CSV file."""
    console.print("[yellow]Glossary import not yet implemented[/yellow]")


# =============================================================================
# Style Commands
# =============================================================================


@cli.group()
def style():
    """Manage translation style templates."""
    pass


@style.command("list")
def style_list() -> None:
    """List available style templates."""
    styles = ["tien_hiep", "kiem_hiep", "huyen_huyen", "do_thi"]
    console.print("[bold]Available styles:[/bold]")
    for s in styles:
        console.print(f"  - {s}")


@style.command("generate")
@click.option("--description", required=True, help="Style description in Vietnamese")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output YAML path")
def style_generate(description: str, output: str) -> None:
    """Generate new style template using LLM."""
    console.print("[yellow]Style generation not yet implemented[/yellow]")


if __name__ == "__main__":
    cli()
