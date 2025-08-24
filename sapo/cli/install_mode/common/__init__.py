"""Common functionality for installation modes."""

from enum import Enum, auto
import subprocess  # nosec B404
import shutil
from pathlib import Path
from typing import Union, Any

# Custom types
PathLike = Union[str, Path]
ConfigDict = dict[str, Any]


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
        result = run_docker_command(
            ["docker", "--version"], check=False, capture_output=True
        )
        return result.returncode == 0
    except (FileNotFoundError, ValueError):
        return False


def run_docker_command(
    cmd: list[str],
    check: bool = True,
    capture_output: bool = True,
    bypass_validation: bool = False,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Securely run Docker commands with proper validation.

    This function addresses Bandit security warnings by:
    - Using full paths to executables
    - Validating that the command is Docker-related
    - Preventing command injection through proper subprocess usage

    Args:
        cmd: Command to run (must start with 'docker' unless bypass_validation=True)
        check: Whether to raise exception on non-zero exit code
        capture_output: Whether to capture stdout/stderr
        bypass_validation: If True, allows non-Docker commands (for testing)
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        subprocess.CompletedProcess: Command result

    Raises:
        ValueError: If command is not a Docker command
        FileNotFoundError: If Docker executable is not found
        subprocess.CalledProcessError: If command fails and check=True
    """
    if not cmd or not isinstance(cmd, list) or len(cmd) == 0:
        raise ValueError("Command must be a non-empty list")

    if not bypass_validation:
        # Validate that this is a Docker command
        if cmd[0] not in ("docker", "docker-compose"):
            raise ValueError(f"Only Docker commands are allowed, got: {cmd[0]}")

        # Get full path to Docker executable for security
        docker_path = shutil.which(cmd[0])
        if docker_path is None:
            raise FileNotFoundError(f"{cmd[0]} executable not found in PATH")

        # Replace the first element with the full path
        secure_cmd = [docker_path] + cmd[1:]
    else:
        # For testing purposes, use the command as-is
        secure_cmd = cmd

    # Set secure defaults for subprocess.run
    secure_kwargs: dict[str, Any] = {
        "check": check,
        "capture_output": capture_output,
        "text": True,
        "shell": False,  # Explicitly disable shell=True for security
    }
    secure_kwargs.update(kwargs)

    return subprocess.run(secure_cmd, **secure_kwargs)  # nosec B603
