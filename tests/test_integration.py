"""Integration tests for archive extraction."""

import os
import shutil
from pathlib import Path

import pytest

from sapo.cli.archive.extractor import extract_archive


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def artifactory_versions() -> list[str]:
    """List of Artifactory versions to test."""
    return ["7.104.9", "7.49.3", "7.49.2"]


def test_extract_artifactory_archive(
    temp_dir: Path, artifactory_versions: list[str]
) -> None:
    """Test extracting Artifactory archives."""
    for version in artifactory_versions:
        # Create test directory
        test_dir = temp_dir / f"artifactory-oss-{version}"
        if test_dir.exists():
            shutil.rmtree(test_dir)

        # Download and extract Artifactory
        archive_path = Path(
            os.path.expanduser(f"~/.cache/sapo/artifactory-oss-{version}.tar.gz")
        )
        if not archive_path.exists():
            pytest.skip(f"Archive not found: {archive_path}")

        # Extract the archive
        success, error = extract_archive(archive_path, test_dir, verbose=True)
        assert success, f"Failed to extract {version}: {error}"

        # Verify directory structure
        assert (test_dir / "app").exists(), f"app directory not found in {version}"
        assert (test_dir / "var").exists(), f"var directory not found in {version}"
        assert (test_dir / "app" / "bin").exists(), (
            f"bin directory not found in {version}"
        )
        assert (test_dir / "app" / "third-party").exists(), (
            f"third-party directory not found in {version}"
        )

        # Verify some key files exist
        assert (test_dir / "app" / "bin" / "artifactoryctl").exists(), (
            f"artifactoryctl not found in {version}"
        )
        assert (test_dir / "app" / "artifactory.product.version.properties").exists(), (
            f"version properties not found in {version}"
        )

        # Clean up
        shutil.rmtree(test_dir)
