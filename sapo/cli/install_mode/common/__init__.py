"""Common functionality for installation modes."""

from enum import Enum
import subprocess


class OperationStatus(str, Enum):
    """Track status of installation operations."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


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
