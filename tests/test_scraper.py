import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from bs4 import BeautifulSoup
from gitbook_scraper import (
    GitbookScraper,
    NavigationExtractionError,
    ContentExtractionError
)

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
def sample_content_html():
    return """
    <main>
        <h1>Page Title</h1>
        <p>Sample content paragraph.</p>
        <script>console.log('remove me')</script>
        <div class="content">
            <p>More content here.</p>
        </div>
    </main>
    """

@pytest.fixture
def scraper():
    return GitbookScraper("https://test.gitbook.io")

def test_url_normalization():
    scraper = GitbookScraper("https://test.gitbook.io/")
    assert scraper.base_url == "https://test.gitbook.io"
    
    scraper = GitbookScraper("https://test.gitbook.io/docs/#section")
    assert scraper.base_url == "https://test.gitbook.io/docs"

def test_navigation_extraction(scraper, mock_response, sample_nav_html):
    with patch('requests.Session.get') as mock_get:
        response = mock_response(sample_nav_html)
        mock_get.return_value = response
        mock_get.return_value.url = "https://test.gitbook.io"
        
        nav = scraper.extract_nav_structure()
        
        assert len(nav) == 2
        assert nav[0]['title'] == "Introduction"
        assert nav[0]['url'] == "https://test.gitbook.io/intro"
        assert nav[1]['title'] == "Basics"
        assert nav[1]['url'] == "https://test.gitbook.io/basics"
        assert len(nav[1]['children']) == 1
        assert nav[1]['children'][0]['title'] == "Getting Started"
        assert nav[1]['children'][0]['url'] == "https://test.gitbook.io/basics/getting-started"

def test_navigation_extraction_failure(scraper, mock_response):
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = mock_response("<div>No nav here</div>")
        
        with pytest.raises(NavigationExtractionError):
            scraper.extract_nav_structure()

def test_content_extraction(scraper, mock_response, sample_content_html):
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = mock_response(sample_content_html)
        content = scraper.fetch_content("https://test.gitbook.io/page")
        
        assert "Sample content paragraph" in content
        assert "More content here" in content
        assert "remove me" not in content

def test_content_extraction_failure(scraper, mock_response):
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = mock_response("<div>No main content</div>")
        
        content = scraper.fetch_content("https://test.gitbook.io/page")
        assert content is None

def test_selector_loading(tmp_path):
    # Test custom selector loading
    selector_file = tmp_path / "selectors.json"
    selector_file.write_text('{"nav": ["custom-nav"], "content": ["custom-content"]}')
    
    scraper = GitbookScraper(
        "https://test.gitbook.io",
        selector_file=str(selector_file)
    )
    
    assert "custom-nav" in scraper.selectors["nav"]
    assert "custom-content" in scraper.selectors["content"]

def test_markdown_generation(scraper):
    nav_structure = [
        {
            'title': 'Test Page',
            'url': 'https://test.gitbook.io/test',
            'level': 1,
            'children': []
        }
    ]
    
    with patch.object(scraper, 'fetch_content') as mock_fetch:
        mock_fetch.return_value = "Test content"
        content = scraper.generate_markdown(nav_structure)
        
        assert "# Test Page" in content
        assert "Test content" in content

def test_rate_limiting(scraper, mock_response):
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = mock_response("", 429)
        content = scraper.fetch_content("https://test.gitbook.io/page")
        
        assert content is None
        assert mock_get.call_count == scraper.retries

def test_toc_generation(scraper):
    nav_structure = [
        {
            'title': 'Introduction',
            'url': 'https://test.gitbook.io/intro',
            'level': 1,
            'children': [
                {
                    'title': 'Getting Started',
                    'url': 'https://test.gitbook.io/intro/start',
                    'level': 2,
                    'children': []
                }
            ]
        }
    ]
    
    toc = scraper.generate_toc_md(nav_structure)
    assert '- [Introduction](#introduction)' in toc
    assert '  - [Getting Started](#getting-started)' in toc

def test_content_with_images(scraper, mock_response):
    """Test content extraction with images."""
    html_with_images = """
    <main>
        <h1>Test Page</h1>
        <p>Some text before image</p>
        <img src="/images/test.png" alt="Test Image">
        <p>Text between images</p>
        <div>
            <img src="https://example.com/full-url.jpg" alt="External Image">
            <p>Some text with <img src="inline.jpg" alt="Inline"> embedded image.</p>
        </div>
    </main>
    """
    
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = mock_response(html_with_images)
        mock_get.return_value.url = "https://test.gitbook.io/page"
        
        content = scraper.fetch_content("https://test.gitbook.io/page")
        
        assert "Test Page" in content
        assert "Some text before image" in content
        assert "![Test Image](https://test.gitbook.io/images/test.png)" in content
        assert "![External Image](https://example.com/full-url.jpg)" in content
        assert "![Inline](https://test.gitbook.io/page/inline.jpg)" in content