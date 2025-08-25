"""Version listing and management module."""

from datetime import datetime
from typing import Optional  # noqa: F401 (kept for exported API types)

import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from ..platform import Platform
from ..size import format_size

console = Console()


def parse_version_from_html(line: str) -> str | None:
    """
    Parse version from HTML link line.

    Args:
        line: HTML line containing version link

    Returns:
        Optional[str]: Version string if found and valid, None otherwise
    """
    if 'href="' not in line or line.endswith('../"'):
        return None

    version = line.split('href="')[1].split("/")[0]
    if not version[0].isdigit():
        return None

    return version


def get_package_info(url: str) -> tuple[str | None, str | None, str]:
    """
    Get package size and last modified timestamp from URL.

    Args:
        url: Package URL

    Returns:
        Tuple[Optional[str], Optional[str], str]: Size, timestamp, and status
    """
    try:
        response = requests.head(url, timeout=5)
        if response.status_code == 200:
            # Format size
            content_length = response.headers.get("content-length")
            size_str = format_size(int(content_length)) if content_length else "N/A"

            # Format timestamp
            last_modified = response.headers.get("last-modified")
            if last_modified:
                try:
                    dt = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    timestamp = last_modified
            else:
                timestamp = "Unknown"

            status = "[green]Available[/]"
        else:
            size_str = "N/A"
            timestamp = "N/A"
            status = f"[red]Not Available ({response.status_code})[/]"
    except Exception as e:
        size_str = "N/A"
        timestamp = "N/A"
        status = f"[red]Error: {str(e)}[/]"

    return size_str, timestamp, status


def get_available_versions(base_url: str) -> list[str]:
    """
    Get list of available versions from the server.

    Args:
        base_url: Base URL to fetch versions from

    Returns:
        List[str]: List of available versions, sorted semantically in descending order

    Raises:
        requests.exceptions.RequestException: If versions cannot be fetched
    """
    try:
        response = requests.get(f"{base_url}/jfrog-artifactory-oss/", timeout=30)
        response.raise_for_status()
    except Exception as e:
        raise requests.exceptions.RequestException(
            f"Error fetching versions: {str(e)}"
        ) from e

    versions = []
    for line in response.text.splitlines():
        version = parse_version_from_html(line)
        if version:
            versions.append(version)

    # Sort versions semantically in descending order
    versions.sort(key=lambda v: [int(x) for x in v.split(".")], reverse=True)
    return versions


def display_versions_table(
    base_url: str,
    versions: list[str],
    platform: Platform,
    package_pattern: str,
    limit: int = 10,
) -> None:
    """
    Display versions in a table with size and timestamp information.

    Args:
        base_url: Base URL for package downloads
        versions: List of versions to display
        platform: Target platform
        package_pattern: Pattern for package filenames
        limit: Maximum number of versions to show (default: 10)
    """
    # Create table
    table = Table(
        title=f"Available Artifactory Versions ({platform.value})",
        show_header=True,
        header_style="bold magenta",
    )

    # Add columns
    table.add_column("Version", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Last Modified", justify="right")
    table.add_column("Status", justify="right")

    # Get the most recent versions (first N after sorting in descending order)
    recent_versions = versions[:limit] if limit > 0 else versions

    # Get package info for each version with progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Fetching version details...", total=len(recent_versions)
        )

        # Get info for each version
        for version in recent_versions:
            url = f"{base_url}/jfrog-artifactory-oss/{version}/{package_pattern.format(version=version)}"
            size, timestamp, status = get_package_info(url)

            # Add row to table
            table.add_row(version, size, timestamp, status)

            # Update progress
            progress.update(task, advance=1)

    # Display table
    console.print(table)
    console.print(
        f"Showing the {len(recent_versions)} most recent versions. Total versions: {len(versions)}"
    )
