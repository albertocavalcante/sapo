"""Tests for critical volume operations - data safety focused."""

import pytest
import subprocess
from unittest.mock import Mock, patch
from pathlib import Path

from sapo.cli.install_mode.docker.volume import VolumeManager, VolumeType
from sapo.cli.install_mode.common import OperationStatus


class TestVolumeManagerCritical:
    """Test critical volume operations for data safety."""

    @pytest.fixture
    def volume_manager(self):
        """Create a VolumeManager for testing."""
        return VolumeManager(console=Mock())

    def test_docker_availability_check(self, volume_manager):
        """Test Docker availability detection."""
        # Mock successful Docker check
        with patch.object(volume_manager, "_run_command") as mock_run:
            mock_run.return_value = Mock(stdout="Docker version 20.10.0")
            assert volume_manager.is_docker_available() is True

        # Mock Docker not available
        with patch.object(volume_manager, "_run_command") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker not found")
            assert volume_manager.is_docker_available() is False

    def test_command_execution_failure_handling(self, volume_manager):
        """Test handling of command execution failures."""
        # Test that CalledProcessError is properly handled
        with patch("shutil.which", return_value="/usr/bin/docker"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    1, ["docker"], stderr="Command failed"
                )

                with pytest.raises(subprocess.CalledProcessError):
                    volume_manager._run_command(["docker", "invalid"])

    def test_volume_creation_success(self, volume_manager):
        """Test successful volume creation."""
        with patch.object(volume_manager, "is_docker_available", return_value=True):
            with patch.object(volume_manager, "_run_command") as mock_run:
                mock_run.return_value = Mock(stdout="")

                volume_name = volume_manager.create_volume(
                    VolumeType.DATA, name_suffix="test", driver="local"
                )

                assert "artifactory_data_test" in volume_name
                mock_run.assert_called()

    def test_volume_creation_docker_unavailable(self, volume_manager):
        """Test volume creation when Docker is unavailable."""
        with patch.object(volume_manager, "is_docker_available", return_value=False):
            with pytest.raises(RuntimeError, match="Docker is not available"):
                volume_manager.create_volume(VolumeType.DATA)

    def test_volume_creation_with_host_path(self, volume_manager):
        """Test volume creation with host path binding."""
        with patch.object(volume_manager, "is_docker_available", return_value=True):
            with patch.object(volume_manager, "_run_command") as mock_run:
                with patch("os.makedirs") as mock_makedirs:
                    mock_run.return_value = Mock(stdout="")

                    host_path = Path("/tmp/test-artifactory")
                    volume_name = volume_manager.create_volume(
                        VolumeType.DATA, host_path=host_path
                    )

                    # Should create directory and call docker volume create
                    mock_makedirs.assert_called_once_with(host_path, exist_ok=True)
                    mock_run.assert_called()
                    assert "artifactory_data" in volume_name

    def test_backup_volume_docker_unavailable(self, volume_manager):
        """Test backup when Docker is unavailable."""
        with patch.object(volume_manager, "is_docker_available", return_value=False):
            status, result_path = volume_manager.backup_volume(
                "test_volume", Path("/tmp/backup")
            )

            assert status == OperationStatus.ERROR
            assert result_path is None

    def test_restore_volume_missing_backup(self, volume_manager):
        """Test restore with missing backup file."""
        with patch("pathlib.Path.exists", return_value=False):
            backup_file = Path("/tmp/nonexistent.tar")
            status, volume_name = volume_manager.restore_volume(backup_file)

            assert status == OperationStatus.ERROR
            assert volume_name is None

    def test_delete_volume_success(self, volume_manager):
        """Test successful volume deletion."""
        with patch.object(volume_manager, "is_docker_available", return_value=True):
            with patch.object(volume_manager, "_run_command") as mock_run:
                mock_run.return_value = Mock(stdout="")

                result = volume_manager.delete_volume("test_volume")
                assert result is True
                mock_run.assert_called()

    def test_delete_volume_failure(self, volume_manager):
        """Test volume deletion failure handling."""
        with patch.object(volume_manager, "is_docker_available", return_value=True):
            with patch.object(volume_manager, "_run_command") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, ["docker"])

                result = volume_manager.delete_volume("test_volume")
                assert result is False

    def test_volume_info_retrieval(self, volume_manager):
        """Test volume information retrieval."""
        with patch.object(volume_manager, "is_docker_available", return_value=True):
            with patch.object(volume_manager, "_run_command") as mock_run:
                # Mock successful inspect response
                mock_run.return_value = Mock(
                    stdout='[{"Name": "test_volume", "Driver": "local"}]'
                )

                info = volume_manager.get_volume_info("test_volume")
                assert info is not None
                assert info.get("Name") == "test_volume"

    def test_volume_info_invalid_json(self, volume_manager):
        """Test handling of invalid JSON in volume info."""
        with patch.object(volume_manager, "is_docker_available", return_value=True):
            with patch.object(volume_manager, "_run_command") as mock_run:
                mock_run.return_value = Mock(stdout="invalid json")

                info = volume_manager.get_volume_info("test_volume")
                assert info is None
