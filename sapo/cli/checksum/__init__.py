"""Checksum verification module."""

import hashlib
from pathlib import Path

import requests
from rich.console import Console

console = Console()


def calculate_sha256(file_path: Path) -> str:
    """
    Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        str: The SHA256 hash of the file
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_checksum(file_path: Path, expected_checksum_url: str) -> bool:
    """
    Verify the checksum of a file against a remote checksum.

    Args:
        file_path: Path to the file to verify
        expected_checksum_url: URL to download the expected checksum from

    Returns:
        bool: True if checksum verification passed, False otherwise
    """
    try:
        # Calculate SHA256 of the file
        calculated_checksum = calculate_sha256(file_path)
        if not calculated_checksum:
            console.print("[red]Failed to calculate checksum[/]")
            return False

        # Get expected checksum from the server
        response = requests.get(expected_checksum_url, timeout=30)  # 30 seconds timeout
        if not response.ok:
            console.print("[red]Failed to download checksum file[/]")
            return False

        expected_checksum = response.text.strip()

        # Compare checksums
        if calculated_checksum != expected_checksum:
            console.print("[red]Checksum mismatch![/]")
            console.print(f"Expected: {expected_checksum}")
            console.print(f"Got:      {calculated_checksum}")
            return False

        console.print("[green]Checksum verification passed[/]")
        return True

    except Exception as e:
        console.print(f"[red]Error verifying checksum: {str(e)}[/]")
        return False
