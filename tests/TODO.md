# Testing TODOs

## Fixing Async CLI Command Tests

The tests in `tests/test_install_docker_cli.py` are currently skipped because they need special handling for async functions in Typer CLI commands. Here's a plan to fix them:

### Problem

The issue is that Typer's `CliRunner.invoke()` doesn't properly handle async functions, leading to:
1. The async function not being properly awaited
2. The mock for `install_docker_sync` not being called
3. The test runner producing warnings about "coroutine was never awaited"

### Solution Options

#### Option 1: Create a sync wrapper for testing

1. Create a synchronous version of the docker CLI command specifically for testing:

```python
# In tests/utils/cli_utils.py or similar
def sync_docker_command(*args, **kwargs):
    """Synchronous wrapper for the async docker command to use in tests."""
    return asyncio.run(docker(*args, **kwargs))
```

2. Patch the CLI app to use this sync version during tests:

```python
# In test_install_docker_cli.py
with mock.patch('sapo.cli.cli.docker', sync_docker_command):
    with mock.patch('sapo.cli.install_mode.docker.install_docker_sync') as mock_install:
        # Run test
```

#### Option 2: Create an async test runner

1. Create a custom async version of CliRunner:

```python
# In tests/utils/cli_utils.py
class AsyncCliRunner(CliRunner):
    """CLI Runner that supports async command functions."""
    
    async def invoke_async(self, app, args, **kwargs):
        """Asynchronous version of invoke."""
        # Logic to handle async commands
        ...
```

2. Use the async runner in tests:

```python
# In test_install_docker_cli.py
@pytest.mark.asyncio
async def test_install_docker_direct_command():
    runner = AsyncCliRunner()
    with mock.patch(...):
        result = await runner.invoke_async(app, args)
        # Test assertions
```

#### Option 3: Convert CLI command to synchronous

This is the simplest option but requires modifying the actual code:

1. Make the CLI command synchronous by wrapping the async parts:

```python
@install_app.command()
def docker(...):
    """Install Artifactory using Docker."""
    # Import locally to avoid circular imports
    from .install_mode.common import check_docker_installed
    
    # Setup logic...
    
    # Call async function synchronously
    return asyncio.run(docker_async(...))
```

2. Move the async implementation to a separate function

### Recommended Approach

Option 1 is recommended as it allows testing without modifying the production code. Steps to implement:

1. Create a test utilities module with the sync wrapper
2. Update the tests to use this wrapper
3. Properly mock the dependencies
4. Run the test with the synchronous CLI runner

Note: When testing async functions, ensure that any dependencies that are also async (like `wait_for_health`) are also properly mocked with synchronous versions for testing. 
