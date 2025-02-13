import pytest
from unittest.mock import Mock
from gitbook_scraper.scraper import GitbookScraper

@pytest.fixture
def mock_response():
    def _mock_response(content: str, status_code: int = 200):
        mock = Mock()
        mock.text = content
        mock.status_code = status_code
        mock.url = "https://test.gitbook.io"
        def raise_for_status():
            if status_code >= 400:
                raise Exception(f"HTTP {status_code}")
        mock.raise_for_status = raise_for_status
        return mock
    return _mock_response

@pytest.fixture
def scraper():
    return GitbookScraper("https://test.gitbook.io")

@pytest.fixture
def sample_nav_html():
    return """
    <nav>
        <ul>
            <li>
                <a href="/intro">Introduction</a>
            </li>
            <li>
                <a href="/basics">Basics</a>
                <ul>
                    <li>
                        <a href="/basics/getting-started">Getting Started</a>
                    </li>
                </ul>
            </li>
        </ul>
    </nav>
    """