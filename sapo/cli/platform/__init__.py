"""Platform detection and configuration module."""

import platform
from enum import Enum


class Platform(str, Enum):
    """Supported platforms for installation."""

    DARWIN = "darwin"
    LINUX = "linux"
    WINDOWS = "windows"


def get_current_platform() -> Platform:
    """
    Detect the current operating system and return the appropriate Platform enum.

    Returns:
        Platform: The current platform enum value

    Raises:
        ValueError: If the current platform is not supported
    """
    system = platform.system().lower()
    if system == "darwin":
        return Platform.DARWIN
    elif system == "linux":
        return Platform.LINUX
    elif system == "windows":
        return Platform.WINDOWS
    else:
        raise ValueError(f"Unsupported operating system: {system}")
