"""Directory management utilities."""

from pathlib import Path
from typing import Optional, List, Tuple, Dict

from . import OperationStatus


def ensure_directories(
    directories: List[Path],
) -> Dict[Path, Tuple[OperationStatus, Optional[str]]]:
    """Ensure all specified directories exist.

    Args:
        directories: List of directories to create

    Returns:
        Dict[Path, Tuple[OperationStatus, Optional[str]]]: Status for each directory
    """
    results = {}
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            results[directory] = (OperationStatus.SUCCESS, None)
        except Exception as e:
            results[directory] = (OperationStatus.ERROR, str(e))

    return results


def create_artifactory_structure(base_dir: Path) -> Dict[str, Path]:
    """Create the standard Artifactory directory structure.

    Args:
        base_dir: Base directory for Artifactory

    Returns:
        Dict[str, Path]: Map of directory names to paths
    """
    # Standard JFrog Artifactory directories
    directories = {
        "var": base_dir,
        "etc": base_dir / "etc",
        "data": base_dir / "data",
        "logs": base_dir / "logs",
        "backup": base_dir / "backup",
        "access": base_dir / "access",
    }

    # Ensure all directories exist
    ensure_directories(list(directories.values()))

    return directories
