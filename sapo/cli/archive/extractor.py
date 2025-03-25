"""Archive extraction utilities."""

import tarfile
import zipfile
import shutil
from pathlib import Path

from rich.console import Console

console = Console()


def extract_archive(archive_path: Path, extract_to: Path) -> bool:
    """
    Extract an archive file to the specified directory.
    Supports tar.gz and zip formats.

    Args:
        archive_path: Path to the archive file
        extract_to: Directory to extract to

    Returns:
        bool: True if extraction was successful, False otherwise
    """
    try:
        # Create extract directory if it doesn't exist
        extract_to.mkdir(parents=True, exist_ok=True)

        # Check file extension
        if archive_path.name.endswith(".tar.gz") or archive_path.name.endswith(".tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                try:
                    tar.extractall(path=extract_to)
                    return True
                except (OSError, PermissionError) as e:
                    console.print(f"[bold red]Error extracting archive: {str(e)}[/]")
                    return False
        elif archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                try:
                    # On Windows, we need to handle paths differently
                    for member in zip_ref.namelist():
                        # Skip directory entries
                        if member.endswith("/"):
                            continue
                        # Get the target path
                        target_path = extract_to / member
                        # Create parent directories if they don't exist
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        # Extract the file
                        with (
                            zip_ref.open(member) as source,
                            open(target_path, "wb") as target,
                        ):
                            shutil.copyfileobj(source, target)
                    return True
                except (OSError, PermissionError) as e:
                    console.print(f"[bold red]Error extracting archive: {str(e)}[/]")
                    return False
        else:
            console.print(
                f"[bold red]Error: Unsupported archive format: {archive_path.suffix}[/]"
            )
            return False

    except (OSError, PermissionError) as e:
        console.print(f"[bold red]Error accessing archive: {str(e)}[/]")
        return False
    except (tarfile.TarError, zipfile.BadZipFile) as e:
        console.print(f"[bold red]Error reading archive: {str(e)}[/]")
        return False
