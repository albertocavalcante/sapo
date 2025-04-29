"""System utilities for handling platform-specific operations."""

import platform
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
from rich.console import Console

from . import OperationStatus

console = Console()


class Platform(str, Enum):
    """Platform types."""

    LINUX = "Linux"
    DARWIN = "Darwin"  # macOS
    WINDOWS = "Windows"
    UNKNOWN = "Unknown"


def get_platform() -> Platform:
    """Get the current platform as an enum."""
    system = platform.system()
    try:
        return Platform(system)
    except ValueError:
        return Platform.UNKNOWN


def set_directory_permissions(
    directory: Path, owner: str, _non_interactive: bool = False
) -> Tuple[OperationStatus, Optional[str]]:
    """Set permissions on a directory based on platform.

    Args:
        directory: Path to set permissions on
        owner: Owner string (e.g., "1030:1030")
        _non_interactive: Skip confirmation prompts (unused)

    Returns:
        Tuple[OperationStatus, Optional[str]]: Status and message
    """
    if not directory.exists():
        return OperationStatus.ERROR, f"Directory {directory} does not exist"

    platform_type = get_platform()

    if platform_type == Platform.WINDOWS:
        # Windows doesn't use the same permission model
        return (
            OperationStatus.WARNING,
            "Permission setting not needed for Windows with Docker bind mounts",
        )

    # For Unix-like systems (Linux and macOS), we'll provide instructions instead of running sudo
    try:
        # Generate instructions for manual permission setting
        instructions = []
        instructions.append(f"chown -R {owner} {directory}")

        if platform_type == Platform.DARWIN:
            instructions.append(f"chmod -R 777 {directory}")

        # Print instructions
        console.print(
            "[yellow]Please run the following commands with sudo to set proper permissions:[/]"
        )
        for cmd in instructions:
            console.print(f"[yellow]sudo {cmd}[/]")

        return (
            OperationStatus.SKIPPED,
            "Permissions must be set manually with admin/sudo privileges",
        )

    except Exception as e:
        return (
            OperationStatus.ERROR,
            f"Error preparing permission instructions: {str(e)}",
        )
