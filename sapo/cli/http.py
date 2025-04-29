"""HTTP client utilities."""

import os
from rich.console import Console
import aiohttp

console = Console()


def debug_print(msg: str, debug: bool = False) -> None:
    """Print debug message if debug mode is enabled."""
    if debug:
        console.print(f"DEBUG: {msg}")


def create_client_session(debug: bool = False) -> aiohttp.ClientSession:
    """Create an aiohttp client session with proxy support if needed.

    This function respects HTTP_PROXY, HTTPS_PROXY, and NO_PROXY environment variables
    to configure the aiohttp client session with proxy support.

    Args:
        debug: Whether to print debug information

    Returns:
        aiohttp.ClientSession: A configured client session with trust_env=True,
            which enables proxy support based on environment variables
    """
    # Get proxy settings from environment variables (just for debug output)
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")

    if https_proxy or http_proxy:
        debug_print(f"Using proxies - HTTP: {http_proxy}, HTTPS: {https_proxy}", debug)
        if no_proxy:
            debug_print(f"NO_PROXY: {no_proxy}", debug)
    else:
        debug_print("No proxies configured", debug)

    # Create ClientSession with trust_env=True to respect proxy environment variables
    return aiohttp.ClientSession(trust_env=True)
