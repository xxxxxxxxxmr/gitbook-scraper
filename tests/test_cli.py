import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock
from gitbook_scraper.cli import main
from gitbook_scraper.exceptions import NavigationExtractionError, ContentExtractionError

@pytest.fixture
def runner():
    """Provides a Click CLI test runner."""
    return CliRunner(mix_stderr=False)

def test_cli_basic_usage(runner):
    """Test basic CLI usage with default options."""
    with patch('gitbook_scraper.cli.GitbookScraper', autospec=True) as MockScraper:
        mock_instance = MockScraper.return_value
        
        result = runner.invoke(main, ['https://test.gitbook.io'])
        
        assert result.exit_code == 0
        MockScraper.assert_called_once()
        mock_instance.scrape.assert_called_once()

def test_cli_with_options(runner):
    """Test CLI with custom options."""
    with patch('gitbook_scraper.cli.GitbookScraper', autospec=True) as MockScraper:
        mock_instance = MockScraper.return_value
        
        result = runner.invoke(main, [
            'https://test.gitbook.io',
            '--output', 'custom.md',
            '--toc',
            '--delay', '1.0',
            '--debug'
        ])
        
        assert result.exit_code == 0
        MockScraper.assert_called_once_with(
            base_url='https://test.gitbook.io',
            output_file='custom.md',
            generate_toc=True,
            delay=1.0,
            retries=3,
            timeout=10,
            debug=True,
            selector_file=None
        )

def test_cli_navigation_error(runner):
    """Test CLI behavior when navigation extraction fails."""
    with patch('gitbook_scraper.cli.GitbookScraper', autospec=True) as MockScraper:
        mock_instance = MockScraper.return_value
        mock_instance.scrape.side_effect = NavigationExtractionError("Failed to extract nav")
        
        result = runner.invoke(main, ['https://test.gitbook.io'])
        
        assert result.exit_code == 1
        assert "Failed to extract nav" in result.output

def test_cli_content_error(runner):
    """Test CLI behavior when content extraction fails."""
    with patch('gitbook_scraper.cli.GitbookScraper', autospec=True) as MockScraper:
        mock_instance = MockScraper.return_value
        mock_instance.scrape.side_effect = ContentExtractionError("Failed to extract content")
        
        result = runner.invoke(main, ['https://test.gitbook.io'])
        
        assert result.exit_code == 1
        assert "Failed to extract content" in result.output

def test_cli_invalid_url(runner):
    """Test CLI behavior with invalid URL."""
    result = runner.invoke(main, ['not-a-url'])
    assert result.exit_code == 1
    assert "Error" in result.output

def test_cli_custom_selectors(runner, tmp_path):
    """Test CLI with custom selector file."""
    selector_file = tmp_path / "selectors.json"
    selector_file.write_text('{"nav": ["custom-nav"]}')
    
    with patch('gitbook_scraper.cli.GitbookScraper', autospec=True) as MockScraper:
        mock_instance = MockScraper.return_value
        
        result = runner.invoke(main, [
            'https://test.gitbook.io',
            '--selector-file', str(selector_file)
        ])
        
        assert result.exit_code == 0
        MockScraper.assert_called_once()
        assert MockScraper.call_args.kwargs['selector_file'] == str(selector_file)