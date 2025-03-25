"""Tests for size formatting utilities."""

import pytest
from sapo.cli.size import format_size


def test_format_size_zero():
    """Test formatting zero bytes."""
    assert format_size(0) == "0.00 KB"


def test_format_size_negative():
    """Test formatting negative bytes."""
    with pytest.raises(ValueError):
        format_size(-1)


def test_format_size_bytes():
    """Test formatting bytes."""
    assert format_size(500) == "0.49 KB"


def test_format_size_kilobytes():
    """Test formatting kilobytes."""
    assert format_size(1024) == "1.00 KB"
    assert format_size(2048) == "2.00 KB"


def test_format_size_megabytes():
    """Test formatting megabytes."""
    assert format_size(1024 * 1024) == "1.00 MB"
    assert format_size(2 * 1024 * 1024) == "2.00 MB"


def test_format_size_gigabytes():
    """Test formatting gigabytes."""
    assert format_size(1024 * 1024 * 1024) == "1.00 GB"
    assert format_size(2 * 1024 * 1024 * 1024) == "2.00 GB"


def test_format_size_precision():
    """Test formatting with different precisions."""
    assert format_size(1024 * 1024 * 1.5) == "1.50 MB"
    assert format_size(1024 * 1024 * 1.234) == "1.23 MB"
