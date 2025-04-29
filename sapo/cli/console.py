"""Console utilities for the Sapo CLI.

This module provides a custom console implementation based on Rich's Console
with additional functionality specific to the Sapo CLI.
"""

from typing import Any

from rich.console import Console as RichConsole
from rich.theme import Theme


class SapoConsole(RichConsole):
    """Custom console for Sapo CLI with additional functionality.

    Extends Rich's Console with Sapo-specific styling and helpers.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the Sapo console with custom theme.

        Args:
            **kwargs: Additional arguments to pass to the Rich Console
        """
        # Define a custom theme with Sapo colors
        theme = Theme(
            {
                "info": "blue",
                "warning": "yellow",
                "error": "bold red",
                "success": "green",
                "command": "bold cyan",
                "path": "cyan",
                "version": "magenta",
            }
        )

        # Initialize the Rich console with our theme
        super().__init__(theme=theme, **kwargs)

    def info(self, message: str) -> None:
        """Print an informational message.

        Args:
            message: The message to print
        """
        self.print(f"[info]{message}[/]")

    def warning(self, message: str) -> None:
        """Print a warning message.

        Args:
            message: The warning message to print
        """
        self.print(f"[warning]{message}[/]")

    def error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: The error message to print
        """
        self.print(f"[error]{message}[/]")

    def success(self, message: str) -> None:
        """Print a success message.

        Args:
            message: The success message to print
        """
        self.print(f"[success]{message}[/]")

    def command(self, cmd: str) -> None:
        """Print a command.

        Args:
            cmd: The command to print
        """
        self.print(f"[command]{cmd}[/]")

    def path(self, path: str) -> None:
        """Print a file path.

        Args:
            path: The path to print
        """
        self.print(f"[path]{path}[/]")

    def version(self, version: str) -> None:
        """Print a version.

        Args:
            version: The version to print
        """
        self.print(f"[version]{version}[/]")

    def header(self, title: str) -> None:
        """Print a section header.

        Args:
            title: The header title
        """
        width = self.width or 80
        padding = "=" * ((width - len(title) - 4) // 2)
        self.print(f"\n{padding} [bold]{title}[/] {padding}")

    def subheader(self, title: str) -> None:
        """Print a subsection header.

        Args:
            title: The subheader title
        """
        width = self.width or 80
        padding = "-" * ((width - len(title) - 4) // 2)
        self.print(f"\n{padding} [bold]{title}[/] {padding}")


# Create a default console instance for easy import
console = SapoConsole()
