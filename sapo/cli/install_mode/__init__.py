"""Installation mode module for Artifactory.

This module handles different installation methods for Artifactory.
"""

from enum import Enum


class InstallMode(str, Enum):
    """Installation mode enum."""

    LOCAL = "local"
    DOCKER = "docker"
    HELM = "helm"


__all__ = ["InstallMode"]
