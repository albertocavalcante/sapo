"""Global pytest configuration.

This file configures pytest behavior for the entire project.
"""

# Configure pytest-asyncio to use function-scoped event loops by default
pytest_plugins = ["pytest_asyncio"]
