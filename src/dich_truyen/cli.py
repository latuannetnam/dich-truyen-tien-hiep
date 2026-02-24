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
# Pipeline Command (Main Workflow)
# =============================================================================


@cli.command()
@click.option("--url", help="Book index page URL (required for new books)")
@click.option("--book-dir", type=click.Path(), help="Existing book directory")
@click.option("--style", default="tien_hiep", help="Translation style template")
@click.option(
    "--format",
    "output_format",
    default="azw3",
    type=click.Choice(["epub", "azw3", "mobi", "pdf"]),
    help="Output format",
)
@click.option("--chapters", help="Chapter range (e.g., 1-100)")
@click.option("--workers", default=3, type=int, help="Number of translation workers")
@click.option("--crawl-only", is_flag=True, help="Stop after crawl phase (no translation)")
@click.option("--translate-only", is_flag=True, help="Skip crawl, only translate existing chapters")
@click.option("--skip-export", is_flag=True, help="Skip export phase")
@click.option("--no-glossary", is_flag=True, help="Disable auto-glossary generation")
@click.option("--glossary", type=click.Path(exists=True), help="Import glossary from CSV before translation")
@click.option("--force", is_flag=True, help="Force re-process all chapters")
@click.pass_context
def pipeline(
    ctx,
    url: Optional[str],
    book_dir: Optional[str],
    style: str,
    output_format: str,
    chapters: Optional[str],
    workers: int,
    crawl_only: bool,
    translate_only: bool,
    skip_export: bool,
    no_glossary: bool,
    glossary: Optional[str],
    force: bool,
) -> None:
    """Run full pipeline: crawl + translate (concurrent) → export.
    
    Uses streaming architecture for concurrent crawl/translate.
    Supports resume from any interruption point.
    
    Examples:
    
        # Full pipeline (crawl + translate + export)
        dich-truyen pipeline --url "https://..."
        
        # Just crawl chapters (review before translation)
        dich-truyen pipeline --url "https://..." --crawl-only
        
        # Translate existing book (skip crawl)
        dich-truyen pipeline --book-dir books/my-book --translate-only
        
        # Use custom glossary
        dich-truyen pipeline --book-dir books/my-book --glossary custom.csv
    """
    from dich_truyen.config import get_config
    from dich_truyen.crawler.downloader import create_book_directory
    from dich_truyen.exporter.calibre import export_book
    from dich_truyen.pipeline.streaming import StreamingPipeline
    from dich_truyen.translator.glossary import Glossary

    # Validate inputs
    if not url and not book_dir:
        console.print("[red]Error: Either --url or --book-dir is required[/red]")
        raise SystemExit(1)
    
    if crawl_only and translate_only:
        console.print("[red]Error: Cannot use both --crawl-only and --translate-only[/red]")
        raise SystemExit(1)

    async def run():
        # Determine book directory
        if book_dir:
            target_dir = Path(book_dir)
            if not target_dir.exists():
                console.print(f"[red]Error: Directory not found: {target_dir}[/red]")
                raise SystemExit(1)
        else:
            target_dir = await create_book_directory(url, get_config().books_dir)
        
        # Import custom glossary if provided
        if glossary:
            console.print(f"[blue]Importing glossary from {glossary}...[/blue]")
            imported = Glossary.from_csv(Path(glossary))
            imported.save(target_dir)
            console.print(f"[green]Imported {len(imported)} glossary entries[/green]")
        
        # Run streaming pipeline (concurrent crawl + translate)
        pipeline_obj = StreamingPipeline(translator_workers=workers)
        result = await pipeline_obj.run(
            book_dir=target_dir,
            url=url if not translate_only else None,  # Skip crawl if translate-only
            chapters_spec=chapters,
            style_name=style,
            auto_glossary=not no_glossary,
            force=force,
            crawl_only=crawl_only,
        )
        
        # Check for errors
        if result.failed_crawl > 0 or result.failed_translate > 0:
            console.print(f"[yellow]Warning: {result.failed_crawl} crawl errors, {result.failed_translate} translate errors[/yellow]")
        
        # Export phase (only if all chapters are done, not cancelled)
        # Use result.all_done which is True only if all chapters translated AND not cancelled
        should_export = (
            not crawl_only 
            and not skip_export 
            and result.all_done
        )
        
        if should_export:
            console.print("\n[bold blue]═══ Exporting ═══[/bold blue]")
            
            export_result = await export_book(
                book_dir=target_dir,
                output_format=output_format,
            )
            
            if not export_result.success:
                console.print(f"[red]Export failed: {export_result.error_message}[/red]")
                raise SystemExit(1)
            
            console.print(f"[green]✓ Exported: {export_result.output_path}[/green]")
        elif crawl_only:
            console.print("\n[dim]Translation/export skipped (--crawl-only)[/dim]")
        elif skip_export:
            console.print("\n[dim]Export skipped (--skip-export)[/dim]")
        elif result.cancelled:
            console.print("\n[yellow]Export skipped (cancelled by user)[/yellow]")
            console.print("[dim]Run 'dich-truyen export' to manually export available chapters[/dim]")
        elif not result.all_done:
            console.print("\n[yellow]Export skipped (not all chapters translated)[/yellow]")
            console.print("[dim]Resume with same command, or run 'dich-truyen export' to export available chapters[/dim]")

    asyncio.run(run())


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
@click.pass_context
def export(
    ctx,
    book_dir: str,
    output_format: str,
) -> None:
    """Export to ebook format.

    Creates EPUB directly from translated chapters using parallel assembly,
    then converts to target format if needed.
    """
    import asyncio
    
    from dich_truyen.exporter.calibre import export_book
    
    result = asyncio.run(export_book(
        book_dir=Path(book_dir),
        output_format=output_format,
    ))

    if not result.success:
        console.print(f"[red]Export failed: {result.error_message}[/red]")
        raise SystemExit(1)

    console.print(f"[green]Book exported: {result.output_path}[/green]")


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
    from dich_truyen.translator.glossary import Glossary
    
    g = Glossary.load(Path(book_dir))
    if not g or len(g) == 0:
        console.print(f"[yellow]No glossary found in {book_dir}[/yellow]")
        return
    
    g.to_csv(Path(output))
    console.print(f"[green]Exported {len(g)} entries to {output}[/green]")


@glossary.command("import")
@click.option("--book-dir", required=True, type=click.Path(exists=True), help="Book directory")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True), help="Input CSV file")
@click.option("--merge/--replace", default=True, help="Merge with existing or replace")
def glossary_import(book_dir: str, input_file: str, merge: bool) -> None:
    """Import glossary from CSV file."""
    from dich_truyen.translator.glossary import Glossary
    
    imported = Glossary.from_csv(Path(input_file))
    
    if merge:
        existing = Glossary.load_or_create(Path(book_dir))
        for entry in imported.entries:
            existing.add(entry)
        existing.save(Path(book_dir))
        console.print(f"[green]Merged {len(imported)} entries (total: {len(existing)})[/green]")
    else:
        imported.save(Path(book_dir))
        console.print(f"[green]Imported {len(imported)} entries (replaced existing)[/green]")


@glossary.command("show")
@click.option("--book-dir", required=True, type=click.Path(exists=True), help="Book directory")
@click.option("--limit", default=50, help="Maximum entries to show")
def glossary_show(book_dir: str, limit: int) -> None:
    """Display glossary contents."""
    from dich_truyen.translator.glossary import Glossary
    
    g = Glossary.load(Path(book_dir))
    if not g or len(g) == 0:
        console.print(f"[yellow]No glossary found in {book_dir}[/yellow]")
        return
    
    console.print(f"[bold]Glossary ({len(g)} entries):[/bold]")
    for i, entry in enumerate(g.entries[:limit]):
        console.print(f"  {entry.chinese} → {entry.vietnamese} [{entry.category}]")
    
    if len(g) > limit:
        console.print(f"  [dim]... and {len(g) - limit} more[/dim]")


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
    from dich_truyen.translator.style import StyleManager
    
    manager = StyleManager()
    styles = manager.list_available()
    
    console.print("[bold]Available styles:[/bold]")
    for s in styles:
        console.print(f"  - {s}")


@style.command("generate")
@click.option("--description", required=True, help="Style description in Vietnamese")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output YAML path")
def style_generate(description: str, output: str) -> None:
    """Generate new style template using LLM."""
    import asyncio
    from pathlib import Path
    from dich_truyen.translator.style import generate_style_from_description

    async def run():
        console.print(f"[blue]Generating style from description...[/blue]")
        console.print(f"[dim]  Description: {description}[/dim]")
        
        style = await generate_style_from_description(description)
        
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        style.to_yaml(output_path)
        
        console.print(f"[green]✓ Style '{style.name}' generated successfully[/green]")
        console.print(f"[dim]  {len(style.guidelines)} guidelines[/dim]")
        console.print(f"[dim]  {len(style.vocabulary)} vocabulary entries[/dim]")
        console.print(f"[dim]  {len(style.examples)} examples[/dim]")

    asyncio.run(run())


# =============================================================================
# UI Command
# =============================================================================


@cli.command()
@click.option("--port", default=8000, type=int, help="API server port")
@click.option("--host", default="127.0.0.1", help="API server host")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def ui(port: int, host: str, no_browser: bool) -> None:
    """Launch web UI in browser.

    Starts the FastAPI API server and the Next.js frontend,
    then opens the UI in your default browser.
    """
    import shutil
    import subprocess
    import threading
    import time
    import webbrowser

    import uvicorn

    from dich_truyen.api.server import create_app
    from dich_truyen.config import get_config

    config = get_config()
    app = create_app(books_dir=config.books_dir.resolve())

    # Locate web/ directory relative to this source file
    web_dir = Path(__file__).resolve().parent.parent.parent / "web"
    if not web_dir.exists():
        console.print(f"[red]Error: Web UI not found at {web_dir}[/red]")
        console.print("[dim]Please ensure the 'web/' directory exists in the project root.[/dim]")
        raise SystemExit(1)

    if not (web_dir / "node_modules").exists():
        console.print("[red]Error: Frontend dependencies not installed.[/red]")
        console.print("[dim]Run: cd web && npm install[/dim]")
        raise SystemExit(1)

    npm_cmd = shutil.which("npm")
    if npm_cmd is None:
        console.print("[red]Error: npm not found. Please install Node.js 18+.[/red]")
        raise SystemExit(1)

    frontend_port = 3000

    # Start Next.js dev server as a subprocess
    next_proc = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--port", str(frontend_port)],
        cwd=str(web_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Auto-open browser pointing to the frontend
    if not no_browser:

        def open_browser() -> None:
            time.sleep(3)
            webbrowser.open(f"http://localhost:{frontend_port}")

        threading.Thread(target=open_browser, daemon=True).start()

    console.print("[bold green]🚀 Dịch Truyện UI starting...[/bold green]")
    console.print(f"[blue]   UI:  http://localhost:{frontend_port}[/blue]")
    console.print(f"[blue]   API: http://{host}:{port}/api/docs[/blue]")
    console.print("[dim]   Press Ctrl+C to stop[/dim]\n")
    import signal

    config_uv = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config_uv)

    # Disable uvicorn's built-in signal handlers to avoid ugly tracebacks
    server.install_signal_handlers = lambda: None  # type: ignore[assignment]

    # Install our own clean Ctrl+C handler
    def _handle_sigint(signum: int, frame: object) -> None:
        server.should_exit = True

    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        server.run()
    except SystemExit:
        pass
    finally:
        console.print("\n[dim]Shutting down...[/dim]")
        next_proc.terminate()
        try:
            next_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            next_proc.kill()


if __name__ == "__main__":
    cli()

