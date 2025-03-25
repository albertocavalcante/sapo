"""File size formatting utilities."""


def format_size(size_bytes: int) -> str:
    """
    Format a size in bytes to a human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size string (e.g., "1.2 GB", "500 MB", "100 KB")

    Raises:
        ValueError: If size_bytes is negative
    """
    if size_bytes < 0:
        raise ValueError("Size cannot be negative")

    if size_bytes == 0:
        return "0.00 KB"

    if size_bytes >= 1024 * 1024 * 1024:  # >= 1GB
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif size_bytes >= 1024 * 1024:  # >= 1MB
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:  # < 1MB
        return f"{size_bytes / 1024:.2f} KB"
