"""CLI entry point for Sapo.

This module provides the entry point for the Sapo CLI application
when run using the 'python -m sapo.cli' command.
"""

from .cli import app


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        app()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
