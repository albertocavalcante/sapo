"""Test release notes functionality."""

import pytest
from unittest.mock import AsyncMock, patch
import aiohttp
from sapo.cli.release_notes import (
    get_map_info,
    get_topics,
    get_release_notes,
    debug_print,
    _find_target_topic,
    _parse_release_content,
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
async def test_get_map_info_success(mock_session):
    """Test successful map info retrieval."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=MOCK_MAP_INFO)

    # Create a context manager that returns the mock response
    cm = AsyncMock()
    cm.__aenter__.return_value = mock_response
    mock_session.get.return_value = cm

    result = await get_map_info(mock_session, debug=True)
    assert result == MOCK_MAP_INFO


@pytest.mark.asyncio
async def test_get_map_info_failure(mock_session):
    """Test map info retrieval failure."""
    mock_response = AsyncMock()
    mock_response.status = 404

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_response
    mock_session.get.return_value = cm

    result = await get_map_info(mock_session, debug=True)
    assert result is None


@pytest.mark.asyncio
async def test_get_topics_success(mock_session):
    """Test successful topics retrieval."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=MOCK_TOPICS)

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_response
    mock_session.get.return_value = cm

    result = await get_topics(mock_session, "/test/topics", debug=True)
    assert result == MOCK_TOPICS


@pytest.mark.asyncio
async def test_get_topics_failure(mock_session):
    """Test topics retrieval failure."""
    mock_response = AsyncMock()
    mock_response.status = 500

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_response
    mock_session.get.return_value = cm

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
    """Test parsing release content."""
    content = MOCK_HTML_CONTENT

    result = await _parse_release_content(content, debug=True)
    assert result is not None
    assert result["release_date"] == "Released: 27 March 2025"
    assert len(result["rows"]) == 2
    assert "Critical" in result["by_severity"]
    assert len(result["by_severity"]["Critical"]) == 1


@pytest.mark.asyncio
async def test_get_release_notes_success():
    """Test successful release notes retrieval."""
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
async def test_get_release_notes_no_version_match():
    """Test release notes retrieval with no matching version."""
    # Mock responses with different version
    different_topics = [{"id": "other-topic", "title": "Other Topic"}]

    map_response = AsyncMock()
    map_response.status = 200
    map_response.json = AsyncMock(return_value=MOCK_MAP_INFO)

    topics_response = AsyncMock()
    topics_response.status = 200
    topics_response.json = AsyncMock(return_value=different_topics)

    # Create context managers for each response
    map_cm = AsyncMock()
    map_cm.__aenter__.return_value = map_response

    topics_cm = AsyncMock()
    topics_cm.__aenter__.return_value = topics_response

    # Create session mock with side effects
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.side_effect = [map_cm, topics_cm]

    # Create session factory mock that returns a context manager
    session_factory = AsyncMock(spec=aiohttp.ClientSession)
    session_factory.__aenter__.return_value = session

    # Test the function
    with patch("aiohttp.ClientSession", return_value=session_factory):
        result = await get_release_notes("7.104.14", debug=True)
        assert result is None


def test_debug_print():
    """Test debug print function."""
    with patch("rich.console.Console.print") as mock_print:
        debug_print("test message", True)
        mock_print.assert_called_once_with("DEBUG: test message")

        mock_print.reset_mock()
        debug_print("test message", False)
        mock_print.assert_not_called()
