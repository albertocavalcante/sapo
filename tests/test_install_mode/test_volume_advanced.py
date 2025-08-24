"""
Advanced tests for Docker volume management functionality.

These tests focus on comprehensive coverage of VolumeManager operations
including edge cases, error scenarios, and data safety operations.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from sapo.cli.install_mode.common import OperationStatus
from sapo.cli.install_mode.docker.volume import VolumeManager, VolumeType


class TestVolumeManagerDockerAvailability:
    """Test Docker availability detection and graceful degradation."""

    def test_docker_available_success(self) -> None:
        """Test successful Docker availability check."""
        manager = VolumeManager()

        with patch.object(manager, "_run_command") as mock_run:
            mock_run.return_value = Mock(stdout="Docker version 20.10.0")

            result = manager.is_docker_available()

            assert result is True
            mock_run.assert_called_once_with(["docker", "--version"])

    def test_docker_not_found_filenotfound(self) -> None:
        """Test Docker not found (FileNotFoundError)."""
        manager = VolumeManager()

        with patch.object(manager, "_run_command") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker: command not found")

            result = manager.is_docker_available()

            assert result is False

    def test_docker_not_found_subprocess_error(self) -> None:
        """Test Docker not available (subprocess error)."""
        manager = VolumeManager()

        with patch.object(manager, "_run_command") as mock_run:
            mock_run.side_effect = subprocess.SubprocessError(
                "Docker daemon not running"
            )

            result = manager.is_docker_available()

            assert result is False

    def test_operations_fail_gracefully_without_docker(self) -> None:
        """Test that operations fail gracefully when Docker is not available."""
        manager = VolumeManager()

        with patch.object(manager, "is_docker_available", return_value=False):
            # Volume listing should return empty list
            volumes = manager.list_volumes()
            assert volumes == []

            # Volume deletion should return False
            result = manager.delete_volume("test_volume")
            assert result is False

            # Backup should return error status
            with tempfile.TemporaryDirectory() as tmpdir:
                backup_path = Path(tmpdir)
                status, path = manager.backup_volume("test_volume", backup_path)
                assert status == OperationStatus.ERROR
                assert path is None

            # Restore should return error status
            with tempfile.TemporaryDirectory() as tmpdir:
                fake_backup = Path(tmpdir) / "backup.tar"
                fake_backup.write_text("fake backup")
                status, volume = manager.restore_volume(fake_backup)
                assert status == OperationStatus.ERROR
                assert volume is None


class TestVolumeManagerCreation:
    """Test volume creation with various configurations."""

    def test_create_volume_basic(self) -> None:
        """Test basic volume creation."""
        manager = VolumeManager(volume_prefix="test")

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            volume_name = manager.create_volume(VolumeType.DATA, name_suffix="basic")

            assert volume_name == "test_data_basic"
            mock_run.assert_called_once()

            # Verify command structure
            cmd = mock_run.call_args[0][0]
            assert cmd[:3] == ["docker", "volume", "create"]
            assert "test_data_basic" in cmd

    def test_create_volume_with_timestamp_suffix(self) -> None:
        """Test volume creation with auto-generated timestamp suffix."""
        manager = VolumeManager(volume_prefix="test")

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command"),
        ):
            volume_name = manager.create_volume(VolumeType.LOGS)

            # Should contain timestamp and follow naming pattern
            assert volume_name.startswith("test_logs_")
            assert len(volume_name.split("_")) == 3  # prefix_type_timestamp

    def test_create_volume_with_driver_and_options(self) -> None:
        """Test volume creation with custom driver and options."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            driver_opts = {"size": "10g", "type": "ext4"}
            manager.create_volume(
                VolumeType.POSTGRESQL,
                name_suffix="custom",
                driver="local",
                driver_opts=driver_opts,
            )

            cmd = mock_run.call_args[0][0]

            # Verify driver is specified
            assert "--driver" in cmd
            assert "local" in cmd

            # Verify driver options
            assert "--opt" in cmd
            opt_args = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--opt"]
            assert "size=10g" in opt_args
            assert "type=ext4" in opt_args

    def test_create_volume_with_host_path(self) -> None:
        """Test volume creation with host path binding."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            host_path = Path(tmpdir) / "artifactory_data"

            with (
                patch.object(manager, "is_docker_available", return_value=True),
                patch.object(manager, "_run_command") as mock_run,
                patch("os.makedirs") as mock_makedirs,
            ):
                manager.create_volume(
                    VolumeType.DATA, name_suffix="bind", host_path=host_path
                )

                # Should create host directory
                mock_makedirs.assert_called_once_with(host_path, exist_ok=True)

                cmd = mock_run.call_args[0][0]

                # Should use local driver for host binding
                assert "--driver" in cmd
                assert "local" in cmd

                # Should have bind mount options
                opt_args = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--opt"]
                assert any("type=none" in opt for opt in opt_args)
                assert any("o=bind" in opt for opt in opt_args)
                assert any(f"device={host_path.absolute()}" in opt for opt in opt_args)

    def test_create_volume_with_custom_labels(self) -> None:
        """Test volume creation with custom labels."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            custom_labels = {"project": "test-project", "environment": "development"}

            manager.create_volume(
                VolumeType.BACKUP,
                name_suffix="labeled",
                labels=custom_labels,
                display_name="Test Backup Volume",
            )

            cmd = mock_run.call_args[0][0]

            # Should have labels
            label_args = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--label"]

            # Check for custom labels
            assert any("project=test-project" in label for label in label_args)
            assert any("environment=development" in label for label in label_args)

            # Check for default system labels
            assert any(
                "com.jfrog.artifactory.managed-by=sapo" in label for label in label_args
            )
            assert any(
                "com.jfrog.artifactory.volume-type=backup" in label
                for label in label_args
            )
            assert any(
                "com.jfrog.artifactory.display-name=Test Backup Volume" in label
                for label in label_args
            )

    def test_create_volume_docker_unavailable_raises_error(self) -> None:
        """Test that volume creation raises error when Docker is unavailable."""
        manager = VolumeManager()

        with patch.object(manager, "is_docker_available", return_value=False):
            with pytest.raises(RuntimeError, match="Docker is not available"):
                manager.create_volume(VolumeType.DATA)

    def test_create_volume_command_failure_raises_error(self) -> None:
        """Test that volume creation raises error when Docker command fails."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "docker volume create"
            )

            with pytest.raises(subprocess.CalledProcessError):
                manager.create_volume(VolumeType.DATA)


class TestVolumeManagerListing:
    """Test volume listing and information retrieval."""

    def test_list_volumes_success(self) -> None:
        """Test successful volume listing."""
        manager = VolumeManager(volume_prefix="test")

        mock_output = "test_data_123,local,/var/lib/docker/volumes/test_data_123\ntest_logs_456,local,/var/lib/docker/volumes/test_logs_456"

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.return_value = Mock(stdout=mock_output)

            volumes = manager.list_volumes()

            assert len(volumes) == 2
            assert volumes[0]["name"] == "test_data_123"
            assert volumes[0]["driver"] == "local"
            assert volumes[1]["name"] == "test_logs_456"

            # Verify command
            cmd = mock_run.call_args[0][0]
            assert "docker" in cmd
            assert "volume" in cmd
            assert "ls" in cmd
            assert "--filter" in cmd
            assert "name=test" in cmd

    def test_list_volumes_empty_output(self) -> None:
        """Test volume listing with no volumes."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.return_value = Mock(stdout="")

            volumes = manager.list_volumes()
            assert volumes == []

    def test_list_volumes_malformed_output(self) -> None:
        """Test volume listing with malformed output."""
        manager = VolumeManager()

        # Output with insufficient columns
        mock_output = "incomplete_line\ntest_volume,local"  # Missing mountpoint

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.return_value = Mock(stdout=mock_output)

            volumes = manager.list_volumes()
            # Should skip malformed lines
            assert volumes == []

    def test_list_volumes_command_error(self) -> None:
        """Test volume listing when command fails."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.side_effect = Exception("Docker error")

            volumes = manager.list_volumes()
            assert volumes == []

    def test_get_volume_info_success(self) -> None:
        """Test successful volume info retrieval."""
        manager = VolumeManager()

        mock_volume_data = [
            {
                "Name": "test_volume",
                "Driver": "local",
                "Mountpoint": "/var/lib/docker/volumes/test_volume/_data",
                "Labels": {"managed-by": "sapo"},
            }
        ]

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.return_value = Mock(stdout=json.dumps(mock_volume_data))

            info = manager.get_volume_info("test_volume")

            assert info is not None
            assert info["Name"] == "test_volume"
            assert info["Driver"] == "local"
            assert "Labels" in info

    def test_get_volume_info_not_found(self) -> None:
        """Test volume info retrieval when volume doesn't exist."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.return_value = Mock(stdout="[]")

            info = manager.get_volume_info("nonexistent_volume")
            assert info is None

    def test_get_volume_info_command_error(self) -> None:
        """Test volume info retrieval when command fails."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.side_effect = Exception("Docker error")

            info = manager.get_volume_info("test_volume")
            assert info is None


class TestVolumeManagerBackupRestore:
    """Test backup and restore operations."""

    def test_backup_volume_success_uncompressed(self) -> None:
        """Test successful volume backup without compression."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_path = Path(tmpdir)

            with (
                patch.object(manager, "is_docker_available", return_value=True),
                patch.object(manager, "_run_command") as mock_run,
                patch.object(
                    manager, "get_volume_info", return_value={"Name": "test_volume"}
                ),
            ):
                status, backup_file = manager.backup_volume(
                    "test_volume", backup_path, compress=False
                )

                assert status == OperationStatus.SUCCESS
                assert backup_file is not None
                assert backup_file.name.startswith("test_volume_")
                assert backup_file.name.endswith(".tar")
                assert not backup_file.name.endswith(".gz")

                # Should call _run_command twice: once for backup, once for volume info
                assert mock_run.call_count >= 1

                # Find the backup command (the longer one with docker run)
                backup_cmd = None
                for call in mock_run.call_args_list:
                    cmd = call[0][0]
                    if "run" in cmd and "alpine" in cmd:
                        backup_cmd = cmd
                        break

                assert backup_cmd is not None
                assert "docker" in backup_cmd
                assert "run" in backup_cmd
                assert "--rm" in backup_cmd
                assert "alpine" in backup_cmd
                assert "tar -cf" in " ".join(backup_cmd)

    def test_backup_volume_success_compressed(self) -> None:
        """Test successful volume backup with compression."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_path = Path(tmpdir)

            with (
                patch.object(manager, "is_docker_available", return_value=True),
                patch.object(manager, "_run_command") as mock_run,
                patch.object(
                    manager, "get_volume_info", return_value={"Name": "test_volume"}
                ),
            ):
                status, backup_file = manager.backup_volume(
                    "test_volume", backup_path, compress=True
                )

                assert status == OperationStatus.SUCCESS
                assert backup_file is not None
                assert backup_file.name.endswith(".tar.gz")

                # Find the backup command (the longer one with docker run)
                backup_cmd = None
                for call in mock_run.call_args_list:
                    cmd = call[0][0]
                    if "run" in cmd and "alpine" in cmd:
                        backup_cmd = cmd
                        break

                assert backup_cmd is not None
                assert "tar -czf" in " ".join(backup_cmd)

    def test_backup_volume_docker_unavailable(self) -> None:
        """Test backup when Docker is unavailable."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_path = Path(tmpdir)

            with patch.object(manager, "is_docker_available", return_value=False):
                status, backup_file = manager.backup_volume("test_volume", backup_path)

                assert status == OperationStatus.ERROR
                assert backup_file is None

    def test_backup_volume_command_failure(self) -> None:
        """Test backup when Docker command fails."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_path = Path(tmpdir)

            with (
                patch.object(manager, "is_docker_available", return_value=True),
                patch.object(manager, "_run_command") as mock_run,
            ):
                mock_run.side_effect = subprocess.CalledProcessError(1, "docker run")

                status, backup_file = manager.backup_volume("test_volume", backup_path)

                assert status == OperationStatus.ERROR
                assert backup_file is None

    def test_restore_volume_to_existing_volume(self) -> None:
        """Test restoring backup to existing volume."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_file = Path(tmpdir) / "test_volume_20240101120000.tar"
            backup_file.write_text("fake backup content")

            with (
                patch.object(manager, "is_docker_available", return_value=True),
                patch.object(manager, "_run_command") as mock_run,
            ):
                status, volume_name = manager.restore_volume(
                    backup_file, volume_name="existing_volume"
                )

                assert status == OperationStatus.SUCCESS
                assert volume_name == "existing_volume"

                # Verify Docker command
                cmd = mock_run.call_args[0][0]
                assert "docker" in cmd
                assert "run" in cmd
                assert "tar -xf" in " ".join(cmd)

    def test_restore_volume_create_new_volume(self) -> None:
        """Test restoring backup to new volume."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_file = Path(tmpdir) / "test_volume_20240101120000.tar.gz"
            backup_file.write_text("fake compressed backup")

            with (
                patch.object(manager, "is_docker_available", return_value=True),
                patch.object(manager, "_run_command"),
                patch.object(manager, "create_volume") as mock_create,
            ):
                mock_create.return_value = "new_restored_volume"

                status, volume_name = manager.restore_volume(
                    backup_file, volume_type=VolumeType.DATA
                )

                assert status == OperationStatus.SUCCESS
                assert volume_name == "new_restored_volume"

                # Verify new volume was created
                mock_create.assert_called_once()
                create_args = mock_create.call_args
                assert create_args[0][0] == VolumeType.DATA  # volume_type
                assert "labels" in create_args[1]
                # backup_file.name.split("_")[0] gives "test" not "test_volume"
                assert (
                    create_args[1]["labels"]["com.jfrog.artifactory.restored-from"]
                    == "test"
                )

    def test_restore_volume_compressed_backup(self) -> None:
        """Test restoring compressed backup."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_file = Path(tmpdir) / "test_volume.tar.gz"
            backup_file.write_text("compressed backup")

            with (
                patch.object(manager, "is_docker_available", return_value=True),
                patch.object(manager, "_run_command") as mock_run,
            ):
                status, volume_name = manager.restore_volume(
                    backup_file, volume_name="target_volume"
                )

                assert status == OperationStatus.SUCCESS

                # Should use gzip extraction
                cmd = mock_run.call_args[0][0]
                assert "tar -xzf" in " ".join(cmd)

    def test_restore_volume_backup_not_found(self) -> None:
        """Test restore when backup file doesn't exist."""
        manager = VolumeManager()

        nonexistent_backup = Path("/nonexistent/backup.tar")

        with patch.object(manager, "is_docker_available", return_value=True):
            status, volume_name = manager.restore_volume(nonexistent_backup)

            assert status == OperationStatus.ERROR
            assert volume_name is None

    def test_restore_volume_missing_parameters(self) -> None:
        """Test restore with missing required parameters."""
        manager = VolumeManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_file = Path(tmpdir) / "backup.tar"
            backup_file.write_text("backup")

            with patch.object(manager, "is_docker_available", return_value=True):
                # Missing both volume_name and volume_type
                status, volume_name = manager.restore_volume(backup_file)

                assert status == OperationStatus.ERROR
                assert volume_name is None


class TestVolumeManagerDeletion:
    """Test volume deletion operations."""

    def test_delete_volume_success(self) -> None:
        """Test successful volume deletion."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            result = manager.delete_volume("test_volume")

            assert result is True

            cmd = mock_run.call_args[0][0]
            assert cmd == ["docker", "volume", "rm", "test_volume"]

    def test_delete_volume_force(self) -> None:
        """Test volume deletion with force flag."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            result = manager.delete_volume("test_volume", force=True)

            assert result is True

            cmd = mock_run.call_args[0][0]
            assert cmd == ["docker", "volume", "rm", "--force", "test_volume"]

    def test_delete_volume_docker_unavailable(self) -> None:
        """Test deletion when Docker is unavailable."""
        manager = VolumeManager()

        with patch.object(manager, "is_docker_available", return_value=False):
            result = manager.delete_volume("test_volume")
            assert result is False

    def test_delete_volume_command_failure(self) -> None:
        """Test deletion when command fails."""
        manager = VolumeManager()

        with (
            patch.object(manager, "is_docker_available", return_value=True),
            patch.object(manager, "_run_command") as mock_run,
        ):
            mock_run.side_effect = Exception("Volume in use")

            result = manager.delete_volume("test_volume")
            assert result is False


class TestVolumeManagerUtilities:
    """Test utility functions and edge cases."""

    def test_get_purpose_for_type(self) -> None:
        """Test volume type purpose mapping."""
        manager = VolumeManager()

        # Test all known volume types
        assert "data storage" in manager._get_purpose_for_type(VolumeType.DATA).lower()
        assert "logs" in manager._get_purpose_for_type(VolumeType.LOGS).lower()
        assert "backup" in manager._get_purpose_for_type(VolumeType.BACKUP).lower()
        assert (
            "database" in manager._get_purpose_for_type(VolumeType.POSTGRESQL).lower()
        )
        assert "configuration" in manager._get_purpose_for_type(VolumeType.ETC).lower()

    def test_volume_manager_custom_prefix_and_console(self) -> None:
        """Test VolumeManager initialization with custom parameters."""
        custom_console = Console()
        manager = VolumeManager(console=custom_console, volume_prefix="custom")

        assert manager.console is custom_console
        assert manager.volume_prefix == "custom"
        assert "sapo" in manager.default_labels["com.jfrog.artifactory.managed-by"]

    def test_run_command_capture_output_false(self) -> None:
        """Test _run_command with capture_output=False."""
        manager = VolumeManager()

        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_run.return_value = mock_process

            result = manager._run_command(["echo", "test"], capture_output=False)

            assert result is mock_process
            mock_run.assert_called_once_with(
                ["echo", "test"], check=True, capture_output=False, text=True
            )

    def test_run_command_no_check(self) -> None:
        """Test _run_command with check=False."""
        manager = VolumeManager()

        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_run.return_value = mock_process

            result = manager._run_command(["echo", "test"], check=False)

            assert result is mock_process
            mock_run.assert_called_once_with(
                ["echo", "test"], check=False, capture_output=True, text=True
            )

    def test_run_command_error_handling(self) -> None:
        """Test _run_command error handling and reporting."""
        manager = VolumeManager()

        with patch("subprocess.run") as mock_run:
            error = subprocess.CalledProcessError(1, ["docker", "fail"])
            mock_run.side_effect = error

            with pytest.raises(subprocess.CalledProcessError):
                manager._run_command(["docker", "fail"])
