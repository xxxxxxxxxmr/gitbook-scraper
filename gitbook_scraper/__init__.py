"""
GitBook Scraper - A tool to scrape and structure GitBook documentation.
"""

from .scraper import GitbookScraper
from .exceptions import (
    GitbookScraperError,
    NavigationExtractionError,
    ContentExtractionError,
    RateLimitError,
    AuthenticationError
)

__version__ = "0.1.0"
__author__ = "Async"
__email__ = "cigarette@keemail.com"

__all__ = [
    'GitbookScraper',
    'GitbookScraperError',
    'NavigationExtractionError',
    'ContentExtractionError',
    'RateLimitError',
    'AuthenticationError'
]