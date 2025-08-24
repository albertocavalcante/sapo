"""Cleanup and signal handling module."""

import signal
import sys
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

# Global set to track temporary files for cleanup
_temp_files: set[Path] = set()


def register_temp_file(file_path: Path) -> None:
    """
    Register a temporary file for cleanup.

    Args:
        file_path: Path to the temporary file
    """
    _temp_files.add(file_path)


def cleanup() -> None:
    """Clean up temporary files on exit."""
    for temp_file in _temp_files:
        try:
            temp_file.unlink(missing_ok=True)
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not delete temporary file {temp_file}: {str(e)}[/]"
            )


def signal_handler(signum: int, frame: Any) -> None:
    """
    Handle interrupt signals.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    console.print("\n[yellow]Operation interrupted by user. Cleaning up...[/]")
    cleanup()
    sys.exit(1)


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful cleanup."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
