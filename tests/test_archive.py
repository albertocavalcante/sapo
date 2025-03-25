"""Tests for archive extraction utilities."""

import os
import tarfile
import zipfile
from pathlib import Path
import platform
import pytest

from sapo.cli.archive import extract_archive


def create_test_tar(tmp_path: Path) -> Path:
    """Create a test tar.gz archive."""
    archive_path = tmp_path / "test.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        # Add a file
        file_path = tmp_path / "test.txt"
        file_path.write_text("test content")
        tar.add(file_path, arcname="test.txt")
        # Add a directory
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        (dir_path / "subfile.txt").write_text("sub content")
        tar.add(dir_path, arcname="test_dir")
    return archive_path


def create_test_zip(tmp_path: Path) -> Path:
    """Create a test zip archive."""
    archive_path = tmp_path / "test.zip"
    with zipfile.ZipFile(archive_path, "w") as zip_ref:
        # Add a file
        file_path = tmp_path / "test.txt"
        file_path.write_text("test content")
        zip_ref.write(file_path, "test.txt")
        # Add a directory
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        (dir_path / "subfile.txt").write_text("sub content")
        zip_ref.write(dir_path / "subfile.txt", "test_dir/subfile.txt")
    return archive_path


def test_extract_tar(tmp_path):
    """Test extracting a tar.gz archive."""
    archive_path = create_test_tar(tmp_path)
    extract_to = tmp_path / "extract"

    success, error = extract_archive(archive_path, extract_to)
    assert success, error
    assert (extract_to / "test.txt").exists()
    assert (extract_to / "test.txt").read_text() == "test content"
    assert (extract_to / "test_dir" / "subfile.txt").exists()
    assert (extract_to / "test_dir" / "subfile.txt").read_text() == "sub content"


def test_extract_zip(tmp_path):
    """Test extracting a zip archive."""
    archive_path = create_test_zip(tmp_path)
    extract_to = tmp_path / "extract"

    success, error = extract_archive(archive_path, extract_to)
    assert success, error
    assert (extract_to / "test.txt").exists()
    assert (extract_to / "test.txt").read_text() == "test content"
    assert (extract_to / "test_dir" / "subfile.txt").exists()
    assert (extract_to / "test_dir" / "subfile.txt").read_text() == "sub content"


def test_extract_nonexistent_archive(tmp_path):
    """Test extracting a nonexistent archive."""
    archive_path = tmp_path / "nonexistent.tar.gz"
    extract_to = tmp_path / "extract"

    success, error = extract_archive(archive_path, extract_to)
    assert not success
    assert error is not None


def test_extract_corrupted_archive(tmp_path):
    """Test extracting a corrupted archive."""
    archive_path = tmp_path / "corrupted.tar.gz"
    archive_path.write_bytes(b"corrupted content")
    extract_to = tmp_path / "extract"

    success, error = extract_archive(archive_path, extract_to)
    assert not success
    assert error is not None


@pytest.mark.skipif(
    platform.system() == "Windows", reason="Permission test not reliable on Windows"
)
def test_extract_permission_error(tmp_path):
    """Test extracting with permission error."""
    archive_path = create_test_tar(tmp_path)
    extract_to = tmp_path / "extract"

    # Create a read-only directory
    extract_to.mkdir()
    os.chmod(extract_to, 0o444)  # Read-only

    success, error = extract_archive(archive_path, extract_to)
    assert not success
    assert error is not None


def test_extract_existing_directory(tmp_path):
    """Test extracting to an existing directory with files."""
    archive_path = create_test_tar(tmp_path)
    extract_to = tmp_path / "extract"
    extract_to.mkdir()
    (extract_to / "existing.txt").write_text("existing content")

    success, error = extract_archive(archive_path, extract_to)
    assert not success
    assert "existing files" in error.lower()
    assert "existing.txt" in error
