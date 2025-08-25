"""Progress tracking utilities."""

from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console()


class ProgressTracker:
    """A context manager for tracking download progress."""

    def __init__(self, description: str, total: int):
        """
        Initialize the progress tracker.

        Args:
            description: Description of the download
            total: Total size in bytes
        """
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        self.task = self.progress.add_task(description, total=total)

    def __enter__(self) -> "ProgressTracker":
        """Start the progress tracking."""
        self.progress.start()
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any
    ) -> None:
        """Stop the progress tracking."""
        self.progress.stop()

    def update(self, advance: int) -> None:
        """Update the progress."""
        self.progress.update(self.task, advance=advance)
