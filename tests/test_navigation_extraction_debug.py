from unittest.mock import patch
import logging
from bs4 import BeautifulSoup

def test_navigation_extraction_debug(scraper, mock_response, sample_nav_html, caplog):
    """Debug test to see what's happening in navigation extraction."""
    caplog.set_level(logging.DEBUG)
    
    with patch('requests.Session.get') as mock_get:
        response = mock_response(sample_nav_html)
        mock_get.return_value = response
        
        # Debug the HTML content
        soup = BeautifulSoup(sample_nav_html, 'html.parser')
        print("\nSample HTML structure:")
        print(soup.prettify())
        
        # Debug the scraper state
        print("\nScraper base URL:", scraper.base_url)
        print("Mock response URL:", response.url)
        
        # Debug the navigation elements found
        nav = soup.find('nav')
        print("\nNavigation element found:", nav is not None)
        if nav:
            print("Links found:", len(nav.find_all('a', href=True)))
            for link in nav.find_all('a', href=True):
                print(f"- Link: {link.get_text(strip=True)} -> {link['href']}")
        
        # Try extraction
        nav_structure = scraper.extract_nav_structure()
        
        # Debug the extracted navigation
        print("\nExtracted navigation structure:")
        print(nav_structure)
        
        # Assertions
        assert nav_structure  # Should not be empty
        assert len(nav_structure) == 2  # Should have 2 top-level items
        assert nav_structure[0]['title'] == "Introduction"
        assert nav_structure[1]['title'] == "Basics"
        assert len(nav_structure[1]['children']) == 1