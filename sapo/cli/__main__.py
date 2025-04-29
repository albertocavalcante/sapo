"""CLI entry point for Sapo."""

from .cli import app


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
