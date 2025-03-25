"""Progress tracking utilities."""

from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
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

    def __enter__(self):
        """Start the progress tracking."""
        self.progress.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the progress tracking."""
        self.progress.stop()

    def update(self, advance: int):
        """Update the progress."""
        self.progress.update(self.task, advance=advance)
