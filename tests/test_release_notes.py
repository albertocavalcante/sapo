"""Test release notes functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from sapo.cli.release_notes import (
    get_map_info,
    get_topics,
    get_release_notes,
    debug_print,
    _find_target_topic,
    _parse_release_content,
    list_available_versions,
    display_release_notes,
)

# Mock data for testing
MOCK_MAP_INFO = {"topicsApiEndpoint": "/api/khub/maps/test-id/topics"}

MOCK_TOPICS = [
    {
        "id": "topic-1",
        "title": "Artifactory 7.104.14 Release Notes",
        "content": "Release notes content",
    }
]

MOCK_HTML_CONTENT = """
<html>
<body>
<p>Released: 27 March 2025</p>
<table class="informaltable">
    <tr>
        <th>JIRA Issue</th>
        <th>Component</th>
        <th>Severity</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>RTDEV-53839</td>
        <td>Conda</td>
        <td>Critical</td>
        <td>Issue with Conda repositories</td>
    </tr>
    <tr>
        <td>RTDEV-53840</td>
        <td>Package</td>
        <td>High</td>
        <td>Package indexing issue</td>
    </tr>
</table>
</body>
</html>
"""


@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    return session


@pytest.mark.asyncio
async def test_get_map_info(mock_session):
    """Test map info retrieval with both success and failure scenarios."""
    # Success case
    mock_response_success = AsyncMock()
    mock_response_success.status = 200
    mock_response_success.json = AsyncMock(return_value=MOCK_MAP_INFO)

    cm_success = AsyncMock()
    cm_success.__aenter__.return_value = mock_response_success

    # Failure case
    mock_response_failure = AsyncMock()
    mock_response_failure.status = 404

    cm_failure = AsyncMock()
    cm_failure.__aenter__.return_value = mock_response_failure

    # Test success case
    mock_session.get.return_value = cm_success
    result = await get_map_info(mock_session, debug=True)
    assert result == MOCK_MAP_INFO

    # Test failure case
    mock_session.get.return_value = cm_failure
    result = await get_map_info(mock_session, debug=True)
    assert result is None


@pytest.mark.asyncio
async def test_get_topics(mock_session):
    """Test topics retrieval with both success and failure scenarios."""
    # Success case
    mock_response_success = AsyncMock()
    mock_response_success.status = 200
    mock_response_success.json = AsyncMock(return_value=MOCK_TOPICS)

    cm_success = AsyncMock()
    cm_success.__aenter__.return_value = mock_response_success

    # Failure case
    mock_response_failure = AsyncMock()
    mock_response_failure.status = 500

    cm_failure = AsyncMock()
    cm_failure.__aenter__.return_value = mock_response_failure

    # Test success case
    mock_session.get.return_value = cm_success
    result = await get_topics(mock_session, "/test/topics", debug=True)
    assert result == MOCK_TOPICS

    # Test failure case
    mock_session.get.return_value = cm_failure
    result = await get_topics(mock_session, "/test/topics", debug=True)
    assert result is None


@pytest.mark.asyncio
async def test_find_target_topic():
    """Test finding target topic."""
    topics = [
        {"id": "topic-1", "title": "Artifactory 7.104.14 Release Notes"},
        {"id": "topic-2", "title": "Artifactory 7.104.15 Release Notes"},
    ]

    # Should find matching topic
    result = await _find_target_topic(topics, "7.104.14", debug=True)
    assert result == topics[0]

    # Should return None for non-matching version
    result = await _find_target_topic(topics, "7.999.999", debug=True)
    assert result is None


@pytest.mark.asyncio
async def test_parse_release_content():
    """Test parsing release content with various inputs."""
    # Test successful parsing
    content = MOCK_HTML_CONTENT
    result = await _parse_release_content(content, debug=True)
    assert result is not None
    assert result["release_date"] == "Released: 27 March 2025"
    assert len(result["rows"]) == 2
    assert "Critical" in result["by_severity"]
    assert len(result["by_severity"]["Critical"]) == 1
    assert result["by_severity"]["Critical"][0]["id"] == "RTDEV-53839"
    assert result["by_severity"]["High"][0]["description"] == "Package indexing issue"

    # Test with missing table
    content_no_table = """
    <html><body><p>Released: 27 March 2025</p></body></html>
    """
    result = await _parse_release_content(content_no_table, debug=True)
    assert result is None


@pytest.mark.asyncio
async def test_get_release_notes_success():
    """Test successful release notes retrieval - complete happy path."""
    # Mock responses
    map_response = AsyncMock()
    map_response.status = 200
    map_response.json = AsyncMock(return_value=MOCK_MAP_INFO)

    topics_response = AsyncMock()
    topics_response.status = 200
    topics_response.json = AsyncMock(return_value=MOCK_TOPICS)

    content_response = AsyncMock()
    content_response.status = 200
    content_response.text = AsyncMock(return_value=MOCK_HTML_CONTENT)

    # Create context managers for each response
    map_cm = AsyncMock()
    map_cm.__aenter__.return_value = map_response

    topics_cm = AsyncMock()
    topics_cm.__aenter__.return_value = topics_response

    content_cm = AsyncMock()
    content_cm.__aenter__.return_value = content_response

    # Create session mock with side effects
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.side_effect = [map_cm, topics_cm, content_cm]

    # Create session factory mock that returns a context manager
    session_factory = AsyncMock(spec=aiohttp.ClientSession)
    session_factory.__aenter__.return_value = session

    # Test the function
    with patch("aiohttp.ClientSession", return_value=session_factory):
        result = await get_release_notes("7.104.14", debug=True)

        assert result is not None
        assert result["version"] == "7.104.14"
        assert result["release_date"] == "Released: 27 March 2025"
        assert "Critical" in result["by_severity"]
        assert len(result["rows"]) == 2
        assert result["rows"][0][0] == "RTDEV-53839"


@pytest.mark.asyncio
async def test_get_release_notes_failure_cases():
    """Test all failure paths in release notes retrieval."""
    # Create session factory for all tests
    session_factory = AsyncMock(spec=aiohttp.ClientSession)

    # Test 1: Map info failure
    session1 = AsyncMock(spec=aiohttp.ClientSession)
    map_response = AsyncMock()
    map_response.status = 500
    map_cm = AsyncMock()
    map_cm.__aenter__.return_value = map_response
    session1.get.return_value = map_cm
    session_factory.__aenter__.return_value = session1

    with patch("aiohttp.ClientSession", return_value=session_factory):
        result = await get_release_notes("7.104.14", debug=True)
        assert result is None

    # Test 2: No topics endpoint
    session2 = AsyncMock(spec=aiohttp.ClientSession)
    map_response = AsyncMock()
    map_response.status = 200
    map_response.json = AsyncMock(return_value={})  # No topics endpoint
    map_cm = AsyncMock()
    map_cm.__aenter__.return_value = map_response
    session2.get.return_value = map_cm
    session_factory.__aenter__.return_value = session2

    with patch("aiohttp.ClientSession", return_value=session_factory):
        result = await get_release_notes("7.104.14", debug=True)
        assert result is None

    # Test 3: Version not found in topics
    session3 = AsyncMock(spec=aiohttp.ClientSession)
    map_response = AsyncMock()
    map_response.status = 200
    map_response.json = AsyncMock(return_value=MOCK_MAP_INFO)
    map_cm = AsyncMock()
    map_cm.__aenter__.return_value = map_response

    topics_response = AsyncMock()
    topics_response.status = 200
    topics_response.json = AsyncMock(
        return_value=[{"id": "other-topic", "title": "Other Topic"}]
    )
    topics_cm = AsyncMock()
    topics_cm.__aenter__.return_value = topics_response

    session3.get.side_effect = [map_cm, topics_cm]
    session_factory.__aenter__.return_value = session3

    with patch("aiohttp.ClientSession", return_value=session_factory):
        result = await get_release_notes("7.104.14", debug=True)
        assert result is None

    # Test 4: Exception handling
    with patch("aiohttp.ClientSession", side_effect=Exception("Test exception")):
        result = await get_release_notes("7.104.14", debug=True)
        assert result is None


@pytest.mark.asyncio
async def test_list_available_versions():
    """Test version listing with various scenarios."""
    mock_html = """
    <html>
    <body>
    <a href="/help/r/jfrog-release-information/artifactory-7.104.14-self-hosted">7.104.14</a>
    <a href="/help/r/jfrog-release-information/artifactory-7.104.15-self-hosted">7.104.15</a>
    <a href="/other-link">Other</a>
    <a>7.104.16</a>
    </body>
    </html>
    """

    # Success case
    response_success = AsyncMock()
    response_success.status = 200
    response_success.text = AsyncMock(return_value=mock_html)
    cm_success = AsyncMock()
    cm_success.__aenter__.return_value = response_success

    # Failure case
    response_failure = AsyncMock()
    response_failure.status = 500
    cm_failure = AsyncMock()
    cm_failure.__aenter__.return_value = response_failure

    # Test success case
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.return_value = cm_success
    session_factory = AsyncMock(spec=aiohttp.ClientSession)
    session_factory.__aenter__.return_value = session

    with patch("aiohttp.ClientSession", return_value=session_factory):
        versions = await list_available_versions(debug=True)
        assert len(versions) == 2
        assert "7.104.14" in versions
        assert "7.104.15" in versions

    # Test failure case
    session.get.return_value = cm_failure
    with patch("aiohttp.ClientSession", return_value=session_factory):
        versions = await list_available_versions(debug=True)
        assert versions == []


@pytest.mark.asyncio
async def test_display_release_notes():
    """Test display of release notes with both success and failure cases."""
    mock_notes = {
        "version": "7.104.14",
        "release_date": "Released: 27 March 2025",
        "headers": ["JIRA Issue", "Component", "Severity", "Description"],
        "rows": [
            ["RTDEV-53839", "Conda", "Critical", "Issue with Conda repositories"],
            ["RTDEV-53840", "Package", "High", "Package indexing issue"],
        ],
        "by_severity": {
            "Critical": [
                {
                    "id": "RTDEV-53839",
                    "component": "Conda",
                    "severity": "Critical",
                    "description": "Issue with Conda repositories",
                }
            ],
            "High": [
                {
                    "id": "RTDEV-53840",
                    "component": "Package",
                    "severity": "High",
                    "description": "Package indexing issue",
                }
            ],
            "Medium": [],
            "Low": [],
        },
        "severity_order": ["Critical", "High", "Medium", "Low"],
    }

    # Test success case
    with (
        patch(
            "sapo.cli.release_notes.get_release_notes",
            AsyncMock(return_value=mock_notes),
        ),
        patch("rich.console.Console.print") as mock_print,
        patch("rich.progress.Progress.__enter__", return_value=MagicMock()),
        patch("rich.progress.Progress.__exit__"),
    ):
        await display_release_notes("7.104.14", debug=True)
        # Simply check that we printed something
        assert mock_print.call_count > 0

    # Test failure case
    with (
        patch("sapo.cli.release_notes.get_release_notes", AsyncMock(return_value=None)),
        patch("rich.console.Console.print") as mock_print,
        patch("rich.progress.Progress.__enter__", return_value=MagicMock()),
        patch("rich.progress.Progress.__exit__"),
    ):
        await display_release_notes("7.104.14", debug=True)
        # Simply check that we printed something
        assert mock_print.call_count > 0


def test_debug_print():
    """Test debug print function behavior."""
    with patch("rich.console.Console.print") as mock_print:
        debug_print("test message", True)
        mock_print.assert_called_once_with("DEBUG: test message")

        mock_print.reset_mock()
        debug_print("test message", False)
        mock_print.assert_not_called()
