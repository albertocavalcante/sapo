"""Release notes module."""

import re
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import aiohttp

from sapo.cli.http import create_client_session

console = Console()

# Base URL and map ID for JFrog's help system
BASE_URL = "https://jfrog.com/help"
MAP_ID = "booxtVWM8HjIoXm7gJVD9A"


def debug_print(msg: str, debug: bool = False) -> None:
    """Print debug message if debug mode is enabled."""
    if debug:
        console.print(f"DEBUG: {msg}")


async def get_map_info(
    session: aiohttp.ClientSession, debug: bool = False
) -> Optional[Dict[str, Any]]:
    """Get map information containing endpoints."""
    url = f"{BASE_URL}/api/khub/maps/{MAP_ID}"
    debug_print(f"Loading map info from: {url}", debug)

    try:
        async with session.get(url) as response:
            if response.status != 200:
                debug_print(
                    f"Failed to load map info. Status: {response.status}", debug
                )
                return None

            return await response.json()
    except Exception as e:
        debug_print(f"Error loading map info: {str(e)}", debug)
        return None


async def get_topics(
    session: aiohttp.ClientSession, topics_endpoint: str, debug: bool = False
) -> Optional[List[Dict[str, Any]]]:
    """Get all topics from the topics endpoint."""
    url = f"{BASE_URL}{topics_endpoint}"
    debug_print(f"Loading topics from: {url}", debug)

    try:
        async with session.get(url) as response:
            if response.status != 200:
                debug_print(f"Failed to load topics. Status: {response.status}", debug)
                return None

            return await response.json()
    except Exception as e:
        debug_print(f"Error loading topics: {str(e)}", debug)
        return None


async def _find_target_topic(
    topics: List[Dict[str, Any]], version: str, debug: bool = False
) -> Optional[Dict[str, Any]]:
    """Find the topic that contains the specified version."""
    debug_print(f"Looking for version {version} in topics", debug)
    for topic in topics:
        if str(version) in str(topic):
            return topic
    debug_print(f"No topic found for version {version}", debug)
    return None


async def _parse_release_content(
    content: str, debug: bool = False
) -> Optional[Dict[str, Any]]:
    """Parse the HTML content of release notes."""
    soup = BeautifulSoup(content, "html.parser")

    # Extract release date
    release_date = ""
    date_p = soup.find("p", string=lambda s: s and "Released:" in s)
    if date_p:
        release_date = date_p.get_text().strip()

    # Extract resolved issues table
    issues_table = soup.find("table", class_="informaltable")
    if not issues_table:
        debug_print("No issues table found in content", debug)
        return None

    # Get headers and rows
    headers = []
    header_row = issues_table.find("tr")
    if header_row:
        headers = [th.get_text().strip() for th in header_row.find_all(["th"])]

    rows = []
    for row in issues_table.find_all("tr")[1:]:  # Skip header row
        cells = [td.get_text().strip() for td in row.find_all(["td"])]
        rows.append(cells)

    # Group issues by severity
    issues = []
    for row in rows:
        if len(row) >= 4:  # JIRA Issue, Component, Severity, Description
            issues.append(
                {
                    "id": row[0],
                    "component": row[1],
                    "severity": row[2],
                    "description": row[3],
                }
            )

    severity_order = ["Critical", "High", "Medium", "Low"]
    by_severity: dict[str, list[dict[str, str]]] = {sev: [] for sev in severity_order}
    for issue in issues:
        sev = issue["severity"]
        if sev in by_severity:
            by_severity[sev].append(issue)

    return {
        "release_date": release_date,
        "headers": headers,
        "rows": rows,
        "by_severity": by_severity,
        "severity_order": severity_order,
    }


async def get_release_notes(
    version: str, debug: bool = False
) -> Optional[Dict[str, Any]]:
    """Get release notes for a specific version."""
    try:
        # Create a client session with proxy support
        async with create_client_session(debug) as session:
            # First, get the map info to find the topics endpoint
            map_info = await get_map_info(session, debug)
            if not map_info:
                debug_print("Failed to get map info", debug)
                return None

            topics_endpoint = map_info.get("topicsApiEndpoint")
            if not topics_endpoint:
                debug_print("No topics endpoint found in map info", debug)
                return None

            # Get all topics
            topics = await get_topics(session, topics_endpoint, debug)
            if not topics:
                debug_print("Failed to get topics", debug)
                return None

            target_topic = await _find_target_topic(topics, version, debug)
            if not target_topic:
                return None

            content_url = (
                f"{BASE_URL}/api/khub/maps/{MAP_ID}/topics/{target_topic['id']}/content"
            )
            async with session.get(content_url) as response:
                if response.status != 200:
                    debug_print(
                        f"Failed to get content. Status: {response.status}", debug
                    )
                    return None

                content = await response.text()

                parsed_content = await _parse_release_content(content, debug)
                if not parsed_content:
                    return None

                # Add version to the result
                parsed_content["version"] = version
                return parsed_content

    except Exception as e:
        debug_print(f"Error: {str(e)}", debug)
        return None


async def list_available_versions(debug: bool = False) -> List[str]:
    """List all available Artifactory versions with release notes."""
    try:
        url = "https://jfrog.com/help/r/jfrog-release-information/artifactory-self-hosted-releases"
        debug_print(f"Loading versions index: {url}", debug)

        # Create a client session with proxy support
        async with create_client_session(debug) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    debug_print("Failed to load versions index", debug)
                    return []

                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")

                # Extract version links
                versions = []
                for link in soup.find_all("a", href=True):
                    # Try to extract version from URL
                    url_match = re.search(
                        r"artifactory-(\d+\.\d+\.\d+)-self-hosted",
                        link["href"],
                    )
                    if url_match:
                        version = url_match.group(1)
                        if version not in versions:
                            versions.append(version)
                            continue

                    # Try to extract version from link text
                    text_match = re.match(r"^\d+\.\d+\.\d+$", link.text.strip())
                    if text_match and link.text.strip() not in versions:
                        versions.append(link.text.strip())

                versions.sort(key=lambda v: [int(x) for x in v.split(".")])
                return versions

    except Exception as e:
        debug_print(f"Error listing versions: {str(e)}", debug)
        return []


async def display_release_notes(version: str, debug: bool = False) -> None:
    """Display release notes for a specific version."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Fetching release notes...", total=None)

        notes = await get_release_notes(version, debug)

        if notes:
            # Title panel
            title = Text(f"Release Notes for Artifactory {version}", style="bold blue")
            if notes["release_date"]:
                title.append(f"\n{notes['release_date']}", style="italic")
            console.print(Panel(title, expand=False))

            # Issues table
            table = Table(
                title="Resolved Issues",
                show_header=True,
                header_style="bold magenta",
                expand=True,
                show_lines=True,
            )

            # Add columns
            for header in notes["headers"]:
                table.add_column(header, overflow="fold")

            # Add rows
            for row in notes["rows"]:
                # Style the severity column
                styled_row = list(row)
                if len(row) >= 3:  # Has severity column
                    severity_style = {
                        "Critical": "red",
                        "High": "yellow",
                        "Medium": "blue",
                        "Low": "green",
                    }.get(row[2], "white")
                    styled_row[2] = Text(row[2], style=severity_style)
                table.add_row(*styled_row)

            console.print(table)

            # Summary section
            console.print("\n[bold]Summary[/bold]\n")

            for severity in notes["severity_order"]:
                issues = notes["by_severity"][severity]
                if issues:
                    severity_style = {
                        "Critical": "red",
                        "High": "yellow",
                        "Medium": "blue",
                        "Low": "green",
                    }.get(severity, "white")

                    console.print(
                        f"\n[bold {severity_style}]{severity} Issues:[/bold {severity_style}]\n"
                    )

                    for issue in issues:
                        desc = re.sub(r"\s+", " ", issue["description"])
                        console.print(
                            f"• [bold cyan]{issue['id']}[/bold cyan] "
                            f"([italic]{issue['component']}[/italic]): {desc}"
                        )

            console.print("\n[dim]End of release notes[/dim]\n")
        else:
            console.print(
                Panel.fit(
                    f"[red]No release notes found for version {version}.[/red]\n"
                    "Please check the version or try again later.",
                    title="Error",
                    border_style="red",
                )
            )
