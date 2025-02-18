import sys
import click
from rich.console import Console
from rich.traceback import install
from typing import Optional
from .scraper import GitbookScraper
from .exceptions import NavigationExtractionError, ContentExtractionError
import urllib.parse

install(show_locals=True)
console = Console()

@click.command()
@click.argument('url', type=str)
@click.option('-o', '--output', default='documentation.md',
              help='Output file path [default: documentation.md]')
@click.option('--toc/--no-toc', default=False,
              help='Generate table of contents [default: False]')
@click.option('--delay', default=0.5, type=float,
              help='Delay between requests in seconds [default: 0.5]')
@click.option('--retries', default=3, type=int,
              help='Number of retries for failed requests [default: 3]')
@click.option('--timeout', default=10, type=int,
              help='Request timeout in seconds [default: 10]')
@click.option('--debug/--no-debug', default=False,
              help='Enable debug logging [default: False]')
@click.option('--selector-file', type=click.Path(exists=True, dir_okay=False),
              help='Path to JSON file with custom CSS selectors')
@click.option('--toc-items', '-t', multiple=True,
              help='Specific TOC items to extract (can be specified multiple times)')
def main(url: str, output: str, toc: bool, delay: float, retries: int,
         timeout: int, debug: bool, selector_file: Optional[str], toc_items: tuple) -> int:
    """Scrape and structure GitBook documentation into a single markdown file."""
    try:
        # Validate URL
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme:
            raise NavigationExtractionError(f"Invalid URL format: {url}. Must include scheme (e.g., https://)")

        scraper = GitbookScraper(
            base_url=url,
            output_file=output,
            generate_toc=toc,
            delay=delay,
            retries=retries,
            timeout=timeout,
            debug=debug,
            selector_file=selector_file,
            toc_items=list(toc_items) if toc_items else None
        )
        
        with console.status("[bold green]Scraping documentation..."):
            scraper.scrape()
        
        console.print(f"\n[bold green]✓[/] Documentation saved to: {output}")
        return 0
        
    except (NavigationExtractionError, ContentExtractionError) as e:
        console.print(f"\n[bold red]Error:[/] {str(e)}")
        if debug:
            console.print_exception()
        sys.exit(1)  # Use sys.exit to ensure proper exit code
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] An unexpected error occurred: {str(e)}")
        if debug:
            console.print_exception()
        sys.exit(1)  # Use sys.exit to ensure proper exit code

if __name__ == '__main__':
    main()