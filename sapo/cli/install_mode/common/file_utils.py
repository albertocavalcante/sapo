"""File operation utilities for installation modes."""

from pathlib import Path
from typing import Optional
import shutil
import typer
from rich.console import Console

from . import OperationStatus

console = Console()


class FileOperationResult:
    """Result of a file operation with status and details."""

    def __init__(
        self, status: OperationStatus, path: Path, message: Optional[str] = None
    ):
        self.status = status
        self.path = path
        self.message = message

    @property
    def success(self) -> bool:
        """Check if the operation was successful."""
        return self.status == OperationStatus.SUCCESS

    @property
    def error(self) -> bool:
        """Check if the operation resulted in an error."""
        return self.status == OperationStatus.ERROR


def safe_write_file(
    path: Path, content: str, non_interactive: bool = False
) -> FileOperationResult:
    """Safely write content to a file, handling conflicts with user prompts.

    Args:
        path: Path to write to
        content: Content to write
        non_interactive: Whether to skip confirmation prompts

    Returns:
        FileOperationResult: Result of the operation
    """
    # Check for directory/file conflicts
    if path.exists():
        if path.is_dir():
            if non_interactive:
                console.print(
                    f"[bold red]Error:[/] Cannot write to {path} - it's a directory"
                )
                return FileOperationResult(
                    OperationStatus.ERROR, path, "Path exists as a directory"
                )

            should_remove = typer.confirm(
                f"A directory exists at {path} but a file is needed. Remove directory?",
                default=False,
            )

            if should_remove:
                try:
                    shutil.rmtree(path)
                    console.print(f"[yellow]Removed directory {path}[/]")
                except Exception as e:
                    console.print(
                        f"[bold red]Error:[/] Failed to remove directory {path}: {e}"
                    )
                    return FileOperationResult(
                        OperationStatus.ERROR,
                        path,
                        f"Failed to remove directory: {str(e)}",
                    )
            else:
                console.print("[yellow]Skipping file creation.[/]")
                return FileOperationResult(
                    OperationStatus.SKIPPED, path, "User chose not to remove directory"
                )

        elif path.is_file():
            if non_interactive:
                # In non-interactive mode, just overwrite the file
                pass
            else:
                should_overwrite = typer.confirm(
                    f"File {path} already exists. Overwrite?", default=True
                )

                if not should_overwrite:
                    console.print("[yellow]Skipping file creation.[/]")
                    return FileOperationResult(
                        OperationStatus.SKIPPED,
                        path,
                        "User chose not to overwrite file",
                    )

    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    try:
        path.write_text(content, encoding="utf-8")
        return FileOperationResult(OperationStatus.SUCCESS, path)
    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to write to {path}: {e}")
        return FileOperationResult(
            OperationStatus.ERROR, path, f"Failed to write file: {str(e)}"
        )
