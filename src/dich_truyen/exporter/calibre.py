"""Calibre ebook-convert integration for exporting to various formats."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from rich.console import Console

from dich_truyen.config import CalibreConfig, get_config
from dich_truyen.formatter.metadata import BookMetadataManager
from dich_truyen.utils.progress import BookProgress

console = Console()


class ExportResult(BaseModel):
    """Result of export operation."""

    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None


class CalibreExporter:
    """Export to ebook formats using Calibre's ebook-convert."""

    SUPPORTED_FORMATS = ["epub", "azw3", "mobi", "pdf"]

    def __init__(self, config: Optional[CalibreConfig] = None):
        """Initialize the exporter.

        Args:
            config: Calibre configuration
        """
        self.config = config or get_config().calibre
        self._calibre_path: Optional[str] = None

    @property
    def calibre_path(self) -> str:
        """Get the path to ebook-convert executable."""
        if self._calibre_path is None:
            self._calibre_path = self._find_calibre()
        return self._calibre_path

    def _find_calibre(self) -> str:
        """Find the ebook-convert executable.

        Returns:
            Path to ebook-convert

        Raises:
            FileNotFoundError: If ebook-convert is not found
        """
        # First check config path
        if self.config.path != "ebook-convert":
            if Path(self.config.path).exists():
                return self.config.path

        # Check if it's in PATH
        ebook_convert = shutil.which("ebook-convert")
        if ebook_convert:
            return ebook_convert

        # Check common installation locations on Windows
        common_paths = [
            Path("C:/Program Files/Calibre2/ebook-convert.exe"),
            Path("C:/Program Files (x86)/Calibre2/ebook-convert.exe"),
            Path.home() / "AppData/Local/Programs/calibre/ebook-convert.exe",
        ]

        for path in common_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError(
            "ebook-convert not found. Please install Calibre or set CALIBRE_PATH environment variable."
        )

    def _build_command(
        self,
        input_path: Path,
        output_path: Path,
        metadata: Optional[BookMetadataManager] = None,
    ) -> list[str]:
        """Build the ebook-convert command.

        Args:
            input_path: Input HTML file
            output_path: Output ebook file
            metadata: Optional book metadata

        Returns:
            Command as list of strings
        """
        cmd = [
            self.calibre_path,
            str(input_path),
            str(output_path),
        ]

        if metadata:
            cmd.extend(metadata.to_calibre_args())

        # Add some sensible defaults
        cmd.extend([
            "--smarten-punctuation",
            "--no-chapters-in-toc",
            "--level1-toc", "//h:h2[@class='chapter-title']",
        ])

        return cmd

    def export(
        self,
        input_html: Path,
        output_format: str,
        metadata: Optional[BookMetadataManager] = None,
        output_dir: Optional[Path] = None,
    ) -> ExportResult:
        """Export HTML to specified ebook format.

        Args:
            input_html: Path to input HTML file
            output_format: Output format (epub, azw3, mobi, pdf)
            metadata: Optional book metadata
            output_dir: Output directory (uses input parent if not specified)

        Returns:
            ExportResult with status and output path
        """
        # Validate format
        output_format = output_format.lower()
        if output_format not in self.SUPPORTED_FORMATS:
            return ExportResult(
                success=False,
                error_message=f"Unsupported format: {output_format}. Supported: {self.SUPPORTED_FORMATS}",
            )

        # Verify input exists
        input_html = Path(input_html)
        if not input_html.exists():
            return ExportResult(
                success=False,
                error_message=f"Input file not found: {input_html}",
            )

        # Determine output path
        if output_dir:
            output_dir = Path(output_dir)
        else:
            output_dir = input_html.parent.parent / "output"

        output_dir.mkdir(parents=True, exist_ok=True)

        output_name = input_html.stem + f".{output_format}"
        output_path = output_dir / output_name

        # Build command
        try:
            cmd = self._build_command(input_html, output_path, metadata)
        except FileNotFoundError as e:
            return ExportResult(success=False, error_message=str(e))

        console.print(f"[blue]Exporting to {output_format.upper()}...[/blue]")

        # Run ebook-convert
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                console.print(f"[green]Export successful: {output_path}[/green]")
                return ExportResult(success=True, output_path=str(output_path))
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                console.print(f"[red]Export failed: {error_msg}[/red]")
                return ExportResult(success=False, error_message=error_msg)

        except subprocess.TimeoutExpired:
            return ExportResult(
                success=False, error_message="Export timed out after 5 minutes"
            )
        except Exception as e:
            return ExportResult(success=False, error_message=str(e))


def export_book(
    book_dir: Path,
    output_format: str = "epub",
    calibre_path: Optional[str] = None,
) -> ExportResult:
    """Export a book to ebook format.

    Args:
        book_dir: Book directory path
        output_format: Output format
        calibre_path: Optional custom Calibre path

    Returns:
        ExportResult
    """
    book_dir = Path(book_dir)
    formatted_html = book_dir / "formatted" / "book.html"

    if not formatted_html.exists():
        return ExportResult(
            success=False,
            error_message=f"Formatted HTML not found. Run 'format' command first: {formatted_html}",
        )

    # Load metadata
    progress = BookProgress.load(book_dir)
    if progress:
        metadata = BookMetadataManager.from_book_progress(progress)
    else:
        metadata = None

    # Create exporter
    config = CalibreConfig()
    if calibre_path:
        config.path = calibre_path

    exporter = CalibreExporter(config)

    return exporter.export(
        input_html=formatted_html,
        output_format=output_format,
        metadata=metadata,
        output_dir=book_dir / "output",
    )
