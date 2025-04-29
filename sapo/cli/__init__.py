"""Sapo CLI package."""

from importlib.metadata import version

try:
    __version__ = version("sapo")
except ImportError:
    # Package is not installed
    __version__ = "0.2.0"

# Export the app for external use
from .cli import app
