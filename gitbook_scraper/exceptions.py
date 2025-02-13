class GitbookScraperError(Exception):
    """Base exception for GitBook scraper errors."""
    pass

class NavigationExtractionError(GitbookScraperError):
    """Raised when navigation structure cannot be extracted."""
    pass

class ContentExtractionError(GitbookScraperError):
    """Raised when content cannot be extracted from a page."""
    pass

class RateLimitError(GitbookScraperError):
    """Raised when rate limiting is detected."""
    pass

class AuthenticationError(GitbookScraperError):
    """Raised when authentication is required."""
    pass