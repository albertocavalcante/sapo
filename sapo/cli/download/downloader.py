"""File download utilities."""

import tempfile
from pathlib import Path

import requests
from rich.console import Console

from sapo.cli.download.progress import ProgressTracker

console = Console()


def download_file(url: str, local_path: Path, timeout: int = 30) -> bool:
    """
    Download a file from a URL with progress bar using Rich.

    Args:
        url: The URL to download from
        local_path: The local path to save the file to
        timeout: Timeout in seconds for the download

    Returns:
        bool: True if download was successful, False otherwise
    """
    # Create parent directory if it doesn't exist
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        console.print(
            f"[bold red]Error creating directory {local_path.parent}: {str(e)}[/]"
        )
        return False

    # Use a temporary file during download
    temp_file = None
    temp_path = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()

        console.print(f"[dim]URL: {url}[/dim]")
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            if total_size == 0:
                console.print(
                    "[yellow]Warning: Content length not provided by server, progress may be inaccurate[/]"
                )

            with ProgressTracker(
                f"Downloading {local_path.name}", total_size
            ) as progress:
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                            progress.update(len(chunk))

        # Move the temp file to the final destination
        try:
            temp_path.rename(local_path)
            return True
        except (OSError, PermissionError) as e:
            console.print(
                f"[bold red]Error moving file to {local_path}: {str(e)}[/]"
            )
            return False

    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__.replace("Exception", "")
        error_msg = str(e) if str(e) else ""
        console.print(f"[bold red]Error: {error_type} failed: {error_msg}[/]")
        return False

    finally:
        # Clean up temp file if it exists
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink(missing_ok=True)
            except PermissionError:
                pass  # Ignore permission errors during cleanup
