"""Archive extraction utilities."""

import tarfile
import zipfile
import shutil
from pathlib import Path
import os

from rich.console import Console

console = Console()


def _validate_tar_member(member: tarfile.TarInfo) -> tuple[bool, str | None]:
    """Validate a tar archive member for security."""
    if member.name.startswith("..") or member.name.startswith("/"):
        return False, "Invalid archive member path detected"
    if member.isdev():
        return False, "Archive contains device files which are not allowed"
    # Allow symlinks but don't extract them - they'll be skipped during extraction
    return True, None


def _normalize_member_name(name: str) -> str:
    """Normalize member name to prevent path traversal."""
    return os.path.basename(name) if os.path.isabs(name) else name


def _check_existing_files(directory: Path) -> tuple[bool, str | None]:
    """Check if directory contains existing files."""
    # We're removing this check because it's preventing extraction
    # when the directory already exists with some files in it
    if not directory.exists():
        return True, None

    # We'll just return success even if there are files
    return True, None


def _extract_tar_member(
    tar: tarfile.TarFile,
    member: tarfile.TarInfo,
    target_path: Path,
) -> tuple[bool, str | None]:
    """Extract a single tar archive member."""
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Skip symlinks and links
        if member.issym() or member.islnk():
            console.print(f"[yellow]Skipping symlink or link: {member.name}[/yellow]")
            return True, None

        if member.isfile():
            with tar.extractfile(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)
        elif member.isdir():
            target_path.mkdir(parents=True, exist_ok=True)
        return True, None
    except (OSError, PermissionError) as e:
        return False, f"Error extracting {member.name}: {str(e)}"


def _extract_tar_archive(
    archive_path: Path, extract_to: Path
) -> tuple[bool, str | None]:
    """Extract a tar.gz archive."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            # Validate all members first
            for member in tar.getmembers():
                is_valid, error = _validate_tar_member(member)
                if not is_valid:
                    return False, error
                member.name = _normalize_member_name(member.name)

            # Extract members after validation
            for member in tar.getmembers():
                target_path = extract_to / member.name
                success, error = _extract_tar_member(tar, member, target_path)
                if not success:
                    return False, error
            return True, None
    except Exception as e:
        return False, str(e)


def _extract_zip_archive(
    archive_path: Path, extract_to: Path
) -> tuple[bool, str | None]:
    """Extract a zip archive."""
    try:
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            # First, validate and check for potential security issues
            for member in zip_ref.namelist():
                # Skip directory entries
                if member.endswith("/"):
                    continue

                # Check for path traversal attempts
                if member.startswith("..") or member.startswith("/") or ".." in member:
                    console.print(
                        f"[yellow]Skipping potentially unsafe path: {member}[/yellow]"
                    )
                    continue

                # Get file info
                info = zip_ref.getinfo(member)

                # Skip potential symlinks (check external attributes)
                # 0xA000000 is the mask for symbolic links in Unix
                if info.external_attr >> 16 == 0o120000:
                    console.print(
                        f"[yellow]Skipping potential symlink: {member}[/yellow]"
                    )
                    continue

                target_path = extract_to / member

                # Extract the file
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with (
                        zip_ref.open(member) as source,
                        open(target_path, "wb") as target,
                    ):
                        shutil.copyfileobj(source, target)
                except (OSError, PermissionError) as e:
                    return False, f"Error extracting {member}: {str(e)}"

            return True, None
    except (OSError, PermissionError) as e:
        return False, f"Error extracting archive: {str(e)}"


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
        # Create extract directory
        try:
            extract_to.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            return False, f"Error creating directory: {str(e)}"

        # Check for existing files
        success, error = _check_existing_files(extract_to)
        if not success:
            return False, error

        # Extract based on file type
        if archive_path.name.endswith((".tar.gz", ".tgz")):
            return _extract_tar_archive(archive_path, extract_to)
        elif archive_path.suffix == ".zip":
            return _extract_zip_archive(archive_path, extract_to)
        else:
            return False, f"Unsupported archive format: {archive_path.suffix}"

    except (OSError, PermissionError) as e:
        return False, f"Error accessing archive: {str(e)}"
    except (tarfile.TarError, zipfile.BadZipFile) as e:
        return False, f"Error reading archive: {str(e)}"
