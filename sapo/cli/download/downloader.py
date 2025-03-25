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
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = Path(temp_file.name)

        try:
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
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive new chunks
                            temp_file.write(chunk)
                            progress.update(len(chunk))

            # Move the temp file to the final destination
            try:
                temp_path.rename(local_path)
                return True
            except (OSError, PermissionError) as e:
                console.print(
                    f"[bold red]Error moving file to {local_path}: {str(e)}[/]"
                )
                temp_path.unlink(missing_ok=True)
                return False

        except requests.Timeout:
            console.print(
                "[bold red]Error: Download timed out. Please check your connection and try again.[/]"
            )
            temp_path.unlink(missing_ok=True)
            return False
        except requests.exceptions.SSLError as e:
            console.print(f"[bold red]Error: SSL verification failed: {str(e)}[/]")
            temp_path.unlink(missing_ok=True)
            return False
        except requests.exceptions.ConnectionError as e:
            console.print(f"[bold red]Error: Connection failed: {str(e)}[/]")
            temp_path.unlink(missing_ok=True)
            return False
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]Error: Download failed: {str(e)}[/]")
            temp_path.unlink(missing_ok=True)
            return False
