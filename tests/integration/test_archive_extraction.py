"""Integration tests for archive extraction."""

import os
import shutil
from pathlib import Path
import pytest
from subprocess import run


@pytest.mark.integration
@pytest.mark.network
def test_install_artifactory(tmp_path):
    """Test installing Artifactory using the CLI."""
    versions = ["7.104.9", "7.49.3", "7.49.2"]

    # Create a tools directory in the temporary path
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Set the installation directory through environment variable
    os.environ["SAPO_INSTALL_DIR"] = str(tools_dir)

    for version in versions:
        # Clean up any existing installation
        install_dir = tools_dir / f"artifactory-oss-{version}"
        if install_dir.exists():
            shutil.rmtree(install_dir)

        # Run the install command
        result = run(
            ["poetry", "run", "python", "-m", "sapo.cli", "install", "-v", version, "-y", "--verbose"],
            capture_output=True,
            text=True,
            env={**os.environ, "SAPO_INSTALL_DIR": str(tools_dir)},
        )

        # Check if installation was successful
        assert result.returncode == 0, f"Installation failed for version {version}: {result.stderr}"

        # Verify installation directory structure
        assert (install_dir / "app").exists(), f"app directory not found in {version}"
        assert (install_dir / "var").exists(), f"var directory not found in {version}"
        assert (install_dir / "app" / "bin").exists(), f"bin directory not found in {version}"
        assert (install_dir / "app" / "third-party").exists(), f"third-party directory not found in {version}"

        # Verify key files
        assert (install_dir / "app" / "bin" / "artifactoryctl").exists(), f"artifactoryctl not found in {version}"
        assert (install_dir / "app" / "artifactory.product.version.properties").exists(), f"version properties not found in {version}"

        # Clean up
        shutil.rmtree(install_dir)
