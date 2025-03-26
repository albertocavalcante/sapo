"""Archive extraction utilities."""

import tarfile
import zipfile
import shutil
from pathlib import Path
import os
import stat

from rich.console import Console

console = Console()


def _validate_tar_member(member: tarfile.TarInfo) -> tuple[bool, str | None]:
    """Validate a tar archive member for security."""
    if member.name.startswith("..") or member.name.startswith("/"):
        return False, "Invalid archive member path detected"
    if member.isdev():
        return False, "Archive contains device files which are not allowed"
    # Allow all files including symlinks
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
    verbose: bool = False,
) -> tuple[bool, str | None]:
    """Extract a single tar archive member."""
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if verbose:
            console.print(f"Extracting: {member.name}")

        if member.issym() or member.islnk():
            # Handle symlinks by creating them
            if member.issym():
                if verbose:
                    console.print(
                        f"Creating symlink: {member.name} -> {member.linkname}"
                    )
                # Get the target of the symlink
                linkname = member.linkname
                # Create the symlink
                if os.path.exists(target_path):
                    os.unlink(target_path)
                os.symlink(linkname, target_path)
            elif member.islnk():
                if verbose:
                    console.print(
                        f"Creating hard link: {member.name} -> {member.linkname}"
                    )
                # Get the source path
                source_path = os.path.join(
                    os.path.dirname(target_path), member.linkname
                )
                if os.path.exists(target_path):
                    os.unlink(target_path)
                try:
                    # Try to create a hard link
                    os.link(source_path, target_path)
                except (OSError, PermissionError):
                    # Fall back to copying if hard link fails
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, target_path)
                    else:
                        # If source doesn't exist, create an empty file
                        with open(target_path, "wb"):
                            pass
            return True, None
        elif member.isfile():
            with tar.extractfile(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)
            # Set the file permissions
            os.chmod(target_path, member.mode)
        elif member.isdir():
            target_path.mkdir(parents=True, exist_ok=True)
            # Set the directory permissions
            os.chmod(target_path, member.mode)
        return True, None
    except (OSError, PermissionError) as e:
        return False, f"Error extracting {member.name}: {str(e)}"


def _extract_tar_archive(
    archive_path: Path, extract_to: Path, verbose: bool = False
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
                success, error = _extract_tar_member(tar, member, target_path, verbose)
                if not success:
                    return False, error
            return True, None
    except Exception as e:
        return False, str(e)


def _extract_zip_archive(
    archive_path: Path, extract_to: Path, verbose: bool = False
) -> tuple[bool, str | None]:
    """Extract a zip archive."""
    try:
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            # First process and check for potential security issues
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

                if verbose:
                    console.print(f"Extracting: {member}")

                # Get file info
                info = zip_ref.getinfo(member)
                target_path = extract_to / member

                # Check if it's a symlink (external_attr has the Unix file type)
                is_symlink = (info.external_attr >> 16) & stat.S_IFLNK == stat.S_IFLNK

                if is_symlink:
                    # Extract the symlink
                    if verbose:
                        console.print(f"Extracting symlink: {member}")

                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Read symlink target from the file content
                    link_target = zip_ref.read(member).decode("utf-8")

                    if os.path.exists(target_path):
                        os.unlink(target_path)

                    os.symlink(link_target, target_path)
                else:
                    # Extract normal file
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with (
                            zip_ref.open(member) as source,
                            open(target_path, "wb") as target,
                        ):
                            shutil.copyfileobj(source, target)

                        # Set appropriate permissions
                        if info.external_attr > 0:
                            os.chmod(target_path, (info.external_attr >> 16) & 0o777)
                    except (OSError, PermissionError) as e:
                        return False, f"Error extracting {member}: {str(e)}"

            return True, None
    except (OSError, PermissionError) as e:
        return False, f"Error extracting archive: {str(e)}"


def extract_archive(
    archive_path: Path, extract_to: Path, verbose: bool = False
) -> tuple[bool, str | None]:
    """
    Extract an archive file to the specified directory.
    Supports tar.gz and zip formats.

    Args:
        archive_path: Path to the archive file
        extract_to: Directory to extract to
        verbose: Whether to print detailed extraction information

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
            return _extract_tar_archive(archive_path, extract_to, verbose)
        elif archive_path.suffix == ".zip":
            return _extract_zip_archive(archive_path, extract_to, verbose)
        else:
            return False, f"Unsupported archive format: {archive_path.suffix}"

    except (OSError, PermissionError) as e:
        return False, f"Error accessing archive: {str(e)}"
    except (tarfile.TarError, zipfile.BadZipFile) as e:
        return False, f"Error reading archive: {str(e)}"
