"""Archive extraction utilities."""

import tarfile
import zipfile
import shutil
from pathlib import Path

from rich.console import Console

console = Console()


def extract_archive(archive_path: Path, extract_to: Path) -> tuple[bool, str | None]:
    """
    Extract an archive file to the specified directory.
    Supports tar.gz and zip formats.

    Args:
        archive_path: Path to the archive file
        extract_to: Directory to extract to

    Returns:
        tuple[bool, str | None]: A tuple containing:
            - bool: True if extraction was successful, False otherwise
            - str | None: Error message if extraction failed, or None if successful
    """
    try:
        # Create extract directory if it doesn't exist
        try:
            extract_to.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            return False, f"Error creating directory: {str(e)}"

        # Check for existing files
        if extract_to.exists():
            existing_files = []
            for item in extract_to.iterdir():
                if item.is_file() or item.is_dir():
                    existing_files.append(item.name)
            if existing_files:
                return (
                    False,
                    f"Directory contains existing files: {', '.join(existing_files)}",
                )

        # Check file extension
        if archive_path.name.endswith(".tar.gz") or archive_path.name.endswith(".tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                try:
                    tar.extractall(path=extract_to)
                    return True, None
                except (OSError, PermissionError) as e:
                    return False, f"Error extracting archive: {str(e)}"
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
                        try:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                        except (OSError, PermissionError) as e:
                            return False, f"Error creating directory: {str(e)}"
                        # Extract the file
                        try:
                            with (
                                zip_ref.open(member) as source,
                                open(target_path, "wb") as target,
                            ):
                                shutil.copyfileobj(source, target)
                        except (OSError, PermissionError) as e:
                            return False, f"Error extracting file: {str(e)}"
                    return True, None
                except (OSError, PermissionError) as e:
                    return False, f"Error extracting archive: {str(e)}"
        else:
            return False, f"Unsupported archive format: {archive_path.suffix}"

    except (OSError, PermissionError) as e:
        return False, f"Error accessing archive: {str(e)}"
    except (tarfile.TarError, zipfile.BadZipFile) as e:
        return False, f"Error reading archive: {str(e)}"
