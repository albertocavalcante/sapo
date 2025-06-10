"""Tests for the docker module."""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from sapo.cli.console import console
from sapo.cli.install_mode.common.file_utils import safe_write_file
from sapo.cli.install_mode.common.system_utils import check_disk_space
from sapo.cli.install_mode.docker import generate_password


class TestDockerUtils:
    """Test utility functions from the Docker module."""

    def test_check_disk_space(self):
        """Test the check_disk_space function."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Mock os.statvfs to return predictable values
            mock_stat = mock.Mock()
            mock_stat.f_bavail = 2621440  # 10GB in blocks
            mock_stat.f_blocks = 5242880  # 20GB in blocks
            mock_stat.f_frsize = 4096  # 4KB block size

            with mock.patch("os.statvfs", return_value=mock_stat):
                free_gb, total_gb, percent_free = check_disk_space(path)

                # Check that the values are correct
                assert free_gb == 10.0
                assert total_gb == 20.0
                assert percent_free == 50.0

    def test_check_disk_space_error(self):
        """Test check_disk_space when an error occurs."""
        with mock.patch("os.statvfs", side_effect=OSError("Test error")):
            # We need to directly check output rather than mocking since we're
            # using the console's print method directly
            free_gb, total_gb, percent_free = check_disk_space(Path("/nonexistent"))

            # Should return default/fallback values
            assert free_gb == 0.0
            assert total_gb == 0.0
            assert percent_free == 0.0

    def test_generate_password(self):
        """Test the generate_password function."""
        # Get password for master key
        password = generate_password("master.key")

        # Check that it's the expected length
        assert len(password) == 32

        # Get it again - should return the same cached password
        password2 = generate_password("master.key")
        assert password == password2

        # Get a different password for a different key
        password3 = generate_password("join.key")
        assert password != password3

        # Check that passwords contain required character types
        def check_password_complexity(pwd):
            has_uppercase = False
            has_lowercase = False
            has_digit = False
            has_special = False

            for char in pwd:
                if char.isupper():
                    has_uppercase = True
                elif char.islower():
                    has_lowercase = True
                elif char.isdigit():
                    has_digit = True
                else:
                    has_special = True

            return has_uppercase and has_lowercase and has_digit and has_special

        assert check_password_complexity(password)
        assert check_password_complexity(password3)

    def test_safe_write_file_new_file(self):
        """Test safe_write_file with a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_file.txt"
            content = "Test content"

            # Write a new file
            result = safe_write_file(path, content)

            # Check result
            assert result.success is True
            assert path.exists()
            assert path.read_text() == content

    def test_safe_write_file_existing_file_non_interactive(self):
        """Test safe_write_file with an existing file in non-interactive mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_file.txt"

            # Create an existing file
            path.write_text("Original content")

            # Write over it in non-interactive mode
            result = safe_write_file(path, "New content", non_interactive=True)

            # Check result
            assert result.success is True
            assert path.read_text() == "New content"

    @mock.patch("sapo.cli.install_mode.common.file_utils.typer.confirm")
    def test_safe_write_file_existing_file_interactive_confirm(self, mock_confirm):
        """Test safe_write_file with an existing file, user confirms overwrite."""
        mock_confirm.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_file.txt"

            # Create an existing file
            path.write_text("Original content")

            # Write over it with confirmation
            result = safe_write_file(path, "New content")

            # Check result
            assert result.success is True
            assert path.read_text() == "New content"

            # Check that confirm was called
            mock_confirm.assert_called_once()
            args = mock_confirm.call_args[0][0]
            assert "already exists" in args

    # The following two tests remain skipped until the FileOperationResult is updated
    @pytest.mark.skip(
        reason="OperationStatus.SKIPPED not fully implemented in file_utils.py"
    )
    @mock.patch("sapo.cli.install_mode.common.file_utils.typer.confirm")
    def test_safe_write_file_existing_file_interactive_cancel(self, mock_confirm):
        """Test safe_write_file with an existing file, user cancels overwrite."""
        mock_confirm.return_value = False

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_file.txt"

            # Create an existing file
            original_content = "Original content"
            path.write_text(original_content)

            # Attempt to write over it but user cancels
            result = safe_write_file(path, "New content")

            # Check result
            assert result.success is False
            assert path.read_text() == original_content

            # Check that confirm was called
            mock_confirm.assert_called_once()

    @pytest.mark.skip(reason="Console mocking not working as expected")
    def test_safe_write_file_directory_non_interactive(self):
        """Test safe_write_file when path is a directory in non-interactive mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_dir"
            path.mkdir()

            # Attempt to write to a directory
            with mock.patch.object(console, "print") as mock_print:
                result = safe_write_file(path, "content", non_interactive=True)

                # Check result
                assert result.success is False

                # Check that an error was printed
                mock_print.assert_called_once()
                args = mock_print.call_args[0][0]
                assert "Error" in args
