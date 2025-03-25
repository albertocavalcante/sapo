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

    Args:
        archive_path: Path to the archive file
        extract_to: Directory to extract to

    Returns:
        bool: True if extraction was successful, False otherwise
    """
    try:
        # Create extract directory if it doesn't exist
        extract_to.mkdir(parents=True, exist_ok=True)

        # Remove all existing files in the target directory
        if extract_to.exists():
            for item in extract_to.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

        # Check file extension
        if archive_path.name.endswith(".tar.gz") or archive_path.name.endswith(".tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=extract_to)
        elif archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(path=extract_to)
        else:
            console.print(
                f"[bold red]Error: Unsupported archive format: {archive_path.suffix}[/]"
            )
            return False

        return True
    except Exception as e:
        console.print(f"[bold red]Error extracting archive: {str(e)}[/]")
        return False
