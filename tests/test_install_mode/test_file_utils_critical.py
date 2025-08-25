"""Critical tests for file operations - focused on data safety and error handling."""

import tempfile
from pathlib import Path
from unittest import mock

from sapo.cli.install_mode.common import OperationStatus
from sapo.cli.install_mode.common.directory_utils import ensure_directories
from sapo.cli.install_mode.common.file_utils import FileOperationResult, safe_write_file


class TestFileOperationSafety:
    """Test file operations for data safety and error handling."""

    def test_safe_write_file_creates_parent_directories(self):
        """Test that parent directories are created when they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Deep nested path that doesn't exist
            nested_file = Path(tmpdir) / "level1" / "level2" / "level3" / "test.txt"
            content = "test content"

            result = safe_write_file(nested_file, content, non_interactive=True)

            assert result.success is True
            assert nested_file.exists()
            assert nested_file.read_text() == content
            assert nested_file.parent.exists()

    def test_safe_write_file_handles_directory_conflict_non_interactive(self):
        """Test handling when target path exists as directory (non-interactive)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory where we want to write a file
            conflict_path = Path(tmpdir) / "conflict"
            conflict_path.mkdir()

            result = safe_write_file(conflict_path, "content", non_interactive=True)

            # Should fail gracefully without removing directory
            assert result.success is False
            assert result.status == OperationStatus.ERROR
            assert "directory" in result.message.lower()
            assert conflict_path.is_dir()  # Directory should still exist

    def test_safe_write_file_overwrite_existing_file_non_interactive(self):
        """Test overwriting existing files in non-interactive mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "existing.txt"
            original_content = "original content"
            new_content = "new content"

            # Create existing file
            test_file.write_text(original_content)

            # Overwrite in non-interactive mode
            result = safe_write_file(test_file, new_content, non_interactive=True)

            assert result.success is True
            assert test_file.read_text() == new_content

    def test_safe_write_file_permission_error_handling(self):
        """Test handling of permission errors during file writing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            # Mock path.write_text to raise PermissionError
            with mock.patch.object(
                Path, "write_text", side_effect=PermissionError("Permission denied")
            ):
                result = safe_write_file(test_file, "content", non_interactive=True)

                assert result.success is False
                assert result.status == OperationStatus.ERROR
                assert (
                    "permission" in result.message.lower()
                    or "failed to write" in result.message.lower()
                )

    def test_safe_write_file_handles_unicode_content(self):
        """Test that Unicode content is handled properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "unicode.txt"
            unicode_content = "Hello 世界 🌍 éñ françáis"

            result = safe_write_file(test_file, unicode_content, non_interactive=True)

            assert result.success is True
            assert test_file.read_text(encoding="utf-8") == unicode_content

    def test_safe_write_file_large_content(self):
        """Test writing large content to ensure reliability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "large.txt"
            # Create content roughly 1MB
            large_content = "x" * (1024 * 1024)

            result = safe_write_file(test_file, large_content, non_interactive=True)

            assert result.success is True
            assert test_file.stat().st_size >= 1024 * 1024
            assert test_file.read_text() == large_content


class TestDirectoryOperationsSafety:
    """Test directory operations for reliability."""

    def test_ensure_directories_creates_nested_structure(self):
        """Test creating deeply nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            directories = [
                base / "app" / "data",
                base / "app" / "logs" / "access",
                base / "app" / "config" / "templates",
                base / "backup" / "daily" / "full",
            ]

            results = ensure_directories(directories)

            # All operations should succeed
            for directory, (status, message) in results.items():
                assert status == OperationStatus.SUCCESS
                assert message is None
                assert directory.exists()
                assert directory.is_dir()

    def test_ensure_directories_handles_existing_directories(self):
        """Test that existing directories are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            existing_dir = base / "existing"
            existing_dir.mkdir(parents=True)

            # Try to "create" existing directory
            results = ensure_directories([existing_dir])

            status, message = results[existing_dir]
            assert status == OperationStatus.SUCCESS
            assert existing_dir.exists()

    def test_ensure_directories_handles_permission_errors(self):
        """Test handling of permission errors during directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            test_dir = base / "restricted"

            # Mock mkdir to raise PermissionError
            with mock.patch.object(
                Path, "mkdir", side_effect=PermissionError("Permission denied")
            ):
                results = ensure_directories([test_dir])

                status, message = results[test_dir]
                assert status == OperationStatus.ERROR
                assert "permission denied" in message.lower()

    def test_ensure_directories_handles_file_conflicts(self):
        """Test handling when directory path exists as a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            conflict_path = base / "conflict"

            # Create a file where we want a directory
            conflict_path.write_text("I'm a file, not a directory")

            # Try to create directory at same path
            results = ensure_directories([conflict_path])

            status, message = results[conflict_path]
            # Should fail because file exists at path
            assert status == OperationStatus.ERROR
            assert conflict_path.is_file()  # Original file should remain


class TestFileOperationEdgeCases:
    """Test edge cases and error conditions in file operations."""

    def test_file_operation_result_properties(self):
        """Test FileOperationResult helper properties."""
        success_result = FileOperationResult(
            OperationStatus.SUCCESS, Path("/test/path"), "Success message"
        )
        assert success_result.success is True
        assert success_result.error is False

        error_result = FileOperationResult(
            OperationStatus.ERROR, Path("/test/path"), "Error message"
        )
        assert error_result.success is False
        assert error_result.error is True

    def test_safe_write_file_empty_content(self):
        """Test writing empty content (valid use case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.txt"

            result = safe_write_file(test_file, "", non_interactive=True)

            assert result.success is True
            assert test_file.read_text() == ""
            assert test_file.stat().st_size == 0

    def test_safe_write_file_whitespace_only_content(self):
        """Test writing whitespace-only content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "whitespace.txt"
            whitespace_content = "   \n\t  \n  "

            result = safe_write_file(
                test_file, whitespace_content, non_interactive=True
            )

            assert result.success is True
            assert test_file.read_text() == whitespace_content
