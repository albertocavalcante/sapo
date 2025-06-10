"""Common functionality for installation modes."""

from enum import Enum, auto
import subprocess
from pathlib import Path
from typing import Union, Dict, Any

# Custom types
PathLike = Union[str, Path]
ConfigDict = Dict[str, Any]


class OperationStatus(Enum):
    """Operation result status codes."""

    SUCCESS = auto()
    ERROR = auto()
    WARNING = auto()
    SKIPPED = auto()  # Added for user-skipped operations


class Platform(str, Enum):
    """Define platform types for installations."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


def check_docker_installed() -> bool:
    """Check if Docker is installed and available.

    Returns:
        bool: True if Docker is installed and available
    """
    try:
        result = subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
