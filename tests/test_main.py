"""Tests for the CLI entry point."""

from unittest.mock import patch
from sapo.cli.__main__ import main


@patch("sapo.cli.__main__.app")
def test_main_success(mock_app):
    """Test that main returns 0 when app() succeeds."""
    mock_app.return_value = None
    result = main()
    assert result == 0
    mock_app.assert_called_once()


@patch("sapo.cli.__main__.app")
def test_main_exception(mock_app):
    """Test that main returns 1 when app() raises an exception."""
    mock_app.side_effect = Exception("Test error")

    # Patch print to capture the error message
    with patch("builtins.print") as mock_print:
        result = main()
        assert result == 1
        mock_print.assert_called_once_with("Error: Test error")


def test_module_execution():
    """Test the main module's behavior when run as a script."""
    # This test is just a placeholder to keep track of the existence of the code
    # Testing the sys.exit call in __main__ is challenging due to import issues
    # The actual functionality of main() is tested in other tests

    # Import the module to ensure it at least loads correctly
    import sapo.cli.__main__

    # Verify the module has the expected structure
    assert hasattr(sapo.cli.__main__, "main")
    assert callable(sapo.cli.__main__.main)
