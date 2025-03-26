"""Tests for Artifactory installation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from sapo.cli.artifactory import (
    ArtifactoryConfig,
    ArtifactoryPackage,
    install_artifactory,
    list_versions,
    show_info,
    get_default_dest_dir,
)
from sapo.cli.platform import Platform


def test_artifactory_package():
    """Test ArtifactoryPackage model."""
    pkg = ArtifactoryPackage(version="1.0.0", platform=Platform.DARWIN)
    assert pkg.version == "1.0.0"
    assert pkg.platform == Platform.DARWIN
    assert pkg.filename == "jfrog-artifactory-oss-1.0.0-darwin.tar.gz"

    # Test Windows package
    pkg = ArtifactoryPackage(version="1.0.0", platform=Platform.WINDOWS)
    assert pkg.filename == "jfrog-artifactory-oss-1.0.0-windows.zip"


def test_artifactory_config():
    """Test ArtifactoryConfig initialization and properties."""
    config = ArtifactoryConfig(
        version="1.0.0",
        platform=Platform.DARWIN,
        dest_dir=Path("/tmp"),
        keep_archive=True,
        verify_checksum=False,
        verbose=True,
    )

    assert config.version == "1.0.0"
    assert config.platform == Platform.DARWIN
    assert config.dest_dir == Path("/tmp")
    assert config.keep_archive is True
    assert config.verify_checksum is False
    assert config.verbose is True
    assert (
        config.base_url
        == "https://releases.jfrog.io/artifactory/bintray-artifactory/org/artifactory/oss"
    )

    # Test properties
    assert isinstance(config.package, ArtifactoryPackage)
    assert (
        config.download_url
        == f"{config.base_url}/jfrog-artifactory-oss/1.0.0/jfrog-artifactory-oss-1.0.0-darwin.tar.gz"
    )
    assert config.extract_path == Path("/tmp/artifactory-oss-1.0.0")
    assert config.download_path == Path(
        "/tmp/jfrog-artifactory-oss-1.0.0-darwin.tar.gz"
    )


def test_artifactory_config_validation():
    """Test ArtifactoryConfig validation."""
    # Test empty version
    with pytest.raises(ValueError, match="Version must be a non-empty string"):
        ArtifactoryConfig(version="")

    # Test invalid version format
    with pytest.raises(
        ValueError,
        match="Version must be in format X.Y.Z where X, Y, and Z are numbers",
    ):
        ArtifactoryConfig(version="1.0")

    # Test non-string version
    with pytest.raises(ValueError, match="Version must be a non-empty string"):
        ArtifactoryConfig(version=None)

    # Test invalid version formats
    invalid_versions = [
        "1",  # Missing minor and patch
        "1.0",  # Missing patch
        "1.0.0.0",  # Too many components
        "1.0.a",  # Non-numeric patch
        "a.b.c",  # Non-numeric components
        "v1.0.0",  # Leading 'v'
        "-1.0.0",  # Negative version
    ]
    for version in invalid_versions:
        with pytest.raises(
            ValueError,
            match="Version must be in format X.Y.Z where X, Y, and Z are numbers",
        ):
            ArtifactoryConfig(version=version)

    # Test valid version formats
    valid_versions = [
        "0.0.0",
        "1.0.0",
        "0.1.0",
        "0.0.1",
        "999.999.999",
    ]
    for version in valid_versions:
        config = ArtifactoryConfig(version=version)
        assert config.version == version


@patch("typer.confirm")
@patch("sapo.cli.artifactory.download_file")
@patch("sapo.cli.artifactory.extract_archive")
@patch("sapo.cli.artifactory.verify_checksum")
@patch("sapo.cli.artifactory.setup_signal_handlers")
@patch("sapo.cli.artifactory.register_temp_file")
def test_install_artifactory_success(
    mock_register_temp,
    mock_setup_signals,
    mock_verify_checksum,
    mock_extract,
    mock_download,
    mock_confirm,
    tmp_path,
):
    """Test successful Artifactory installation."""
    # Mock user confirmations
    mock_confirm.return_value = True

    # Mock successful operations
    mock_download.return_value = True
    mock_extract.return_value = (True, None)
    mock_verify_checksum.return_value = True

    # Run installation
    install_artifactory(
        version="7.98.17",
        platform=Platform.DARWIN,
        destination=tmp_path,
        verify_checksum_enabled=True,
        verbose=False,
    )

    # Verify all expected functions were called
    mock_setup_signals.assert_called_once()
    mock_confirm.assert_called_once()
    mock_download.assert_called_once()
    mock_verify_checksum.assert_called_once()
    mock_extract.assert_called_once()
    mock_register_temp.assert_called_once()


@patch("typer.confirm")
def test_install_artifactory_user_cancelled(mock_confirm, tmp_path):
    """Test Artifactory installation cancelled by user."""
    mock_confirm.return_value = False

    with pytest.raises(typer.Exit):
        install_artifactory(
            version="7.98.17", platform=Platform.DARWIN, destination=tmp_path
        )


@patch("typer.confirm")
@patch("sapo.cli.artifactory.download_file")
def test_install_artifactory_download_failed(mock_download, mock_confirm, tmp_path):
    """Test Artifactory installation with download failure."""
    mock_confirm.return_value = True
    mock_download.return_value = False

    with pytest.raises(typer.Exit):
        install_artifactory(
            version="7.98.17", platform=Platform.DARWIN, destination=tmp_path
        )


@patch("typer.confirm")
@patch("sapo.cli.artifactory.download_file")
@patch("sapo.cli.artifactory.verify_checksum")
def test_install_artifactory_checksum_failed(
    mock_verify_checksum, mock_download, mock_confirm, tmp_path
):
    """Test Artifactory installation with checksum verification failure."""
    mock_confirm.return_value = True
    mock_download.return_value = True
    mock_verify_checksum.return_value = False

    with pytest.raises(typer.Exit):
        install_artifactory(
            version="7.98.17",
            platform=Platform.DARWIN,
            destination=tmp_path,
            verify_checksum_enabled=True,
        )


@patch("requests.head")
def test_show_info_success(mock_head, tmp_path):
    """Test showing installation info with successful URL check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    config = ArtifactoryConfig(
        version="1.0.0", platform=Platform.DARWIN, dest_dir=tmp_path
    )

    show_info(config)
    mock_head.assert_called_once()


@patch("requests.head")
def test_show_info_failure(mock_head, tmp_path):
    """Test showing installation info with failed URL check."""
    mock_head.side_effect = Exception("Network error")

    config = ArtifactoryConfig(
        version="1.0.0", platform=Platform.DARWIN, dest_dir=tmp_path
    )

    show_info(config)
    mock_head.assert_called_once()


@patch("sapo.cli.version.get_available_versions")
@patch("sapo.cli.version.display_versions_table")
def test_list_versions_success(mock_display, mock_get_versions):
    """Test successful version listing."""
    mock_get_versions.return_value = ["7.98.17", "7.98.16", "7.98.15"]
    list_versions()

    mock_get_versions.assert_called_once()
    mock_display.assert_called_once()


@patch("sapo.cli.version.get_available_versions")
def test_list_versions_error(mock_get_versions):
    """Test version listing with error."""
    mock_get_versions.side_effect = Exception("Network error")

    with pytest.raises(typer.Exit):
        list_versions()


def test_get_default_dest_dir_windows():
    """Test default destination directory for Windows."""
    with patch("pathlib.Path.home", return_value=Path("/home/user")):
        path = get_default_dest_dir(Platform.WINDOWS)
        assert path == Path("/home/user/AppData/Local/Programs/Artifactory")


def test_get_default_dest_dir_darwin():
    """Test default destination directory for macOS."""
    with patch("pathlib.Path.home", return_value=Path("/home/user")):
        path = get_default_dest_dir(Platform.DARWIN)
        assert path == Path("/home/user/dev/tools")


def test_get_default_dest_dir_linux():
    """Test default destination directory for Linux."""
    with patch("pathlib.Path.home", return_value=Path("/home/user")):
        path = get_default_dest_dir(Platform.LINUX)
        assert path == Path("/home/user/dev/tools")


@patch("sapo.cli.artifactory.download_file")
@patch("sapo.cli.artifactory.extract_archive")
@patch("sapo.cli.artifactory.verify_checksum")
@patch("sapo.cli.artifactory.setup_signal_handlers")
@patch("sapo.cli.artifactory.register_temp_file")
def test_install_artifactory_non_interactive(
    mock_register_temp,
    mock_setup_signals,
    mock_verify_checksum,
    mock_extract,
    mock_download,
    tmp_path,
):
    """Test non-interactive Artifactory installation."""
    # Mock successful operations
    mock_download.return_value = True
    mock_extract.return_value = (True, None)
    mock_verify_checksum.return_value = True

    # Run installation in non-interactive mode
    install_artifactory(
        version="7.98.17",
        platform=Platform.DARWIN,
        destination=tmp_path,
        verify_checksum_enabled=True,
        non_interactive=True,
        verbose=True,
    )

    # Verify all expected functions were called but not user confirmation
    mock_setup_signals.assert_called_once()
    mock_download.assert_called_once()
    mock_verify_checksum.assert_called_once()
    mock_extract.assert_called_once()
    mock_register_temp.assert_called_once()


@patch("typer.confirm")
@patch("sapo.cli.artifactory.download_file")
@patch("sapo.cli.artifactory.extract_archive")
def test_install_artifactory_extract_failed(
    mock_extract, mock_download, mock_confirm, tmp_path
):
    """Test Artifactory installation with extraction failure."""
    mock_confirm.return_value = True
    mock_download.return_value = True
    mock_extract.return_value = (False, "Extraction error message")

    with pytest.raises(typer.Exit):
        install_artifactory(
            version="7.98.17",
            platform=Platform.DARWIN,
            destination=tmp_path,
        )
