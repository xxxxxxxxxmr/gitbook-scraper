# GitBook Scraper

A command-line tool to scrape and structure GitBook documentation into a single, well-organized markdown file.

## Features

- 📚 Scrapes any GitBook documentation site
- 🌳 Maintains original document hierarchy and structure
- 📝 Generates a single, well-formatted markdown file
- ⚡ Fast and polite scraping with rate limiting
- 🛠️ Configurable output format and structure
- 🔄 Automatic retry on failed requests
- 📋 Table of contents generation
- 🎯 Selective TOC item extraction

## Installation

```bash
pip install gitbook-scraper
```

## Quick Start

```bash
# Basic usage
gitbook-scraper https://your-gitbook-url.io

# Specify output file
gitbook-scraper https://your-gitbook-url.io -o documentation.md

# With table of contents
gitbook-scraper https://your-gitbook-url.io --toc

# Custom rate limiting
gitbook-scraper https://your-gitbook-url.io --delay 1.0

# Extract specific TOC items
gitbook-scraper https://your-gitbook-url.io -t "Getting Started" -t "Advanced Topics"
```

## Advanced Usage

### Command Line Options

```bash
Options:
  -o, --output TEXT     Output file path [default: documentation.md]
  --toc                 Generate table of contents [default: False]
  --delay FLOAT        Delay between requests in seconds [default: 0.5]
  --retries INTEGER    Number of retries for failed requests [default: 3]
  --timeout INTEGER    Request timeout in seconds [default: 10]
  --debug             Enable debug logging [default: False]
  --no-cleanup        Keep intermediate files [default: False]
  -t, --toc-items TEXT  Specific TOC items to extract (can be specified multiple times)
  --help             Show this message and exit
```

### Python API

```python
from gitbook_scraper import GitbookScraper

# Basic usage
scraper = GitbookScraper(
    base_url="https://your-gitbook-url.io",
    output_file="documentation.md",
    generate_toc=True,
    delay=0.5
)

# Extract specific TOC items
scraper = GitbookScraper(
    base_url="https://your-gitbook-url.io",
    output_file="documentation.md",
    generate_toc=True,
    toc_items=["Getting Started", "Advanced Topics"]
)

scraper.scrape()
```

## Configuration

The tool can be configured using environment variables:

```bash
# Set default output directory
export GITBOOK_SCRAPER_OUTPUT_DIR="./docs"

# Set custom user agent
export GITBOOK_SCRAPER_USER_AGENT="Custom User Agent"

# Set default delay
export GITBOOK_SCRAPER_DELAY=1.0
```

## Error Handling

The scraper implements automatic retries with exponential backoff for failed requests. Common issues and solutions:

- Rate limiting: Increase the delay between requests
- Timeout errors: Increase the timeout value
- Navigation extraction fails: Try different selectors with `--selector-file`

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/feature`)
3. Commit your changes (`git commit -m 'Add feature'`)
4. Push to the branch (`git push origin feature/feature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.