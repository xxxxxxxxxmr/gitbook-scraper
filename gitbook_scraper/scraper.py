#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set, List, Dict, Optional
import logging
import time
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, TextColumn
import json
from .exceptions import NavigationExtractionError, ContentExtractionError

class GitbookScraper:
    """Main scraper class for GitBook documentation sites."""
    
    def __init__(
        self,
        base_url: str,
        output_file: str = "documentation.md",
        generate_toc: bool = False,
        delay: float = 0.5,
        retries: int = 3,
        timeout: int = 10,
        debug: bool = False,
        selector_file: Optional[str] = None
    ):
        """
        Initialize the GitBook scraper.
        
        Args:
            base_url: Base URL of the GitBook site
            output_file: Path to output markdown file
            generate_toc: Whether to generate table of contents
            delay: Delay between requests in seconds
            retries: Number of retries for failed requests
            timeout: Request timeout in seconds
            debug: Enable debug logging
            selector_file: Optional JSON file with custom CSS selectors
        """
        self.base_url = self.normalize_url(base_url)
        self.domain = urlparse(self.base_url).netloc
        self.output_file = Path(output_file)
        self.generate_toc = generate_toc
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        
        # Setup logging
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=log_level, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Initialize session and state
        self.session = requests.Session()
        self.visited_urls: Set[str] = set()
        self.nav_structure: List[Dict] = []
        self.content_cache: Dict[str, str] = {}
        
        # Load custom selectors if provided
        self.selectors = self.load_selectors(selector_file)
        
        # Setup session
        self.session.headers.update({
            'User-Agent': self.get_user_agent()
        })

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL to prevent duplicates."""
        parsed = urlparse(url)
        cleaned = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/'),
            parsed.params,
            parsed.query,
            ''
        ))
        return cleaned.rstrip('/')

    @staticmethod
    def load_selectors(selector_file: Optional[str]) -> Dict:
        """Load custom CSS selectors from JSON file."""
        default_selectors = {
            'nav': ['nav', 'div.sidebar', 'div[class*="sidebar"]'],
            'content': ['main', 'article', 'div.page-inner'],
            'title': ['h1', 'title', 'div.page-title']
        }
        
        if not selector_file:
            return default_selectors
            
        try:
            with open(selector_file) as f:
                custom_selectors = json.load(f)
                return {**default_selectors, **custom_selectors}
        except Exception as e:
            logging.warning(f"Failed to load custom selectors: {e}")
            return default_selectors

    @staticmethod
    def get_user_agent() -> str:
        """Get user agent string from environment or use default."""
        import os
        return os.getenv(
            'GITBOOK_SCRAPER_USER_AGENT',
            'GitBook Scraper/0.1.0 (https://github.com/yourusername/gitbook-scraper)'
        )

    def extract_nav_structure(self) -> List[Dict]:
        """Extract navigation structure from GitBook's sidebar."""
        for attempt in range(self.retries):
            try:
                response = self.session.get(self.base_url, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try different navigation selectors
                nav = None
                for selector in self.selectors['nav']:
                    nav = soup.select_one(selector)
                    if nav:
                        logging.debug(f"Found navigation using selector: {selector}")
                        break
                
                if not nav:
                    logging.debug("Navigation element not found, trying fallback selectors")
                    nav = soup.find('nav') or soup.find('div', {'class': lambda x: x and ('nav' in x.lower() or 'sidebar' in x.lower())})
                
                if not nav:
                    raise NavigationExtractionError("Could not find navigation structure")

                def process_nav_item(element) -> List[Dict]:
                    items = []
                    
                    # First, handle links in list items
                    for li in element.find_all('li', recursive=False):
                        link = li.find('a', href=True)  # Find first link in list item
                        if not link:
                            continue
                            
                        href = link['href']
                        url = urljoin(self.base_url, href) if not href.startswith(('http://', 'https://')) else href
                        
                        if urlparse(url).netloc == self.domain:
                            item = {
                                'title': link.get_text(strip=True),
                                'url': self.normalize_url(url),
                                'level': len(li.find_parents('ul')),
                                'children': []
                            }
                            
                            # Process any nested lists in this list item
                            nested_ul = li.find('ul')
                            if nested_ul:
                                item['children'].extend(process_nav_item(nested_ul))
                                
                            items.append(item)
                            logging.debug(f"Added nav item: {item['title']} -> {item['url']}")
                    
                    return items

                nav_items = process_nav_item(nav.find('ul') or nav)
                if not nav_items:
                    logging.warning("No navigation items found")
                    continue
                    
                logging.debug(f"Found {len(nav_items)} top-level navigation items")
                return nav_items
                
            except Exception as e:
                logging.error(f"Error extracting navigation: {str(e)}")
                if attempt < self.retries - 1:
                    time.sleep(self.delay * (attempt + 1))
                else:
                    raise NavigationExtractionError("Failed to extract navigation after retries")

    def fetch_content(self, url: str) -> Optional[str]:
        """Fetch and process content from a URL."""
        if url in self.content_cache:
            return self.content_cache[url]

        for attempt in range(self.retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try multiple content selectors to find the main content
                content = None
                for selector in [
                    'main article',
                    'main',
                    'article',
                    'div[class*="page-inner"]',
                    'div[class*="content"]',
                    *self.selectors['content']
                ]:
                    content = soup.select_one(selector)
                    if content:
                        logging.debug(f"Found content using selector: {selector}")
                        break
                
                if not content:
                    raise ContentExtractionError(f"No content found for {url}")

                # Remove unnecessary elements
                for element in content.find_all(['script', 'style', 'nav']):
                    element.decompose()
                
                def process_element(element) -> str:
                    """Process individual elements maintaining proper spacing."""
                    if isinstance(element, str):
                        return element.strip()
                    
                    if not hasattr(element, 'name'):
                        return ''
                    
                    # Handle different types of elements
                    if element.name == 'img':
                        img_src = element.get('src', '')
                        img_alt = element.get('alt', '')
                        if img_src:
                            if not img_src.startswith(('http://', 'https://')):
                                img_src = urljoin(url, img_src)
                            # Add warning about image access if it's a GitBook URL
                            if 'gitbook.io' in img_src:
                                return f"\n\n> [!NOTE] Image: {img_alt}\n> Original URL: {img_src}\n> (Note: This image requires authentication)\n\n"
                            return f"\n\n![{img_alt}]({img_src})\n\n"
                    
                    elif element.name in ['p', 'div']:
                        parts = []
                        for child in element.children:
                            if isinstance(child, str):
                                text = child.strip()
                                if text:
                                    parts.append(text)
                            elif child.name == 'img':
                                img_src = child.get('src', '')
                                img_alt = child.get('alt', '')
                                if img_src:
                                    if not img_src.startswith(('http://', 'https://')):
                                        img_src = urljoin(url, img_src)
                                    if 'gitbook.io' in img_src:
                                        parts.append(f"\n\n> [!NOTE] Image: {img_alt}\n> Original URL: {img_src}\n> (Note: This image requires authentication)\n\n")
                                    else:
                                        parts.append(f"\n\n![{img_alt}]({img_src})\n\n")
                            elif child.name in ['br']:
                                parts.append('\n')
                            else:
                                parts.append(process_element(child))
                        return ' '.join(filter(None, parts))
                    
                    elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        level = int(element.name[1])
                        return f"\n\n{'#' * level} {element.get_text(strip=True)}\n\n"
                    
                    elif element.name == 'code':
                        return f"`{element.get_text(strip=True)}`"
                    
                    elif element.name == 'pre':
                        code = element.find('code')
                        if code:
                            lang = code.get('class', [''])[0].replace('language-', '') if code.get('class') else ''
                            return f"\n```{lang}\n{code.get_text(strip=True)}\n```\n"
                        return f"\n```\n{element.get_text(strip=True)}\n```\n"
                    
                    elif element.name == 'ul':
                        items = []
                        for li in element.find_all('li', recursive=False):
                            items.append(f"* {process_element(li)}")
                        return '\n' + '\n'.join(items) + '\n'
                    
                    elif element.name == 'ol':
                        items = []
                        for i, li in enumerate(element.find_all('li', recursive=False), 1):
                            items.append(f"{i}. {process_element(li)}")
                        return '\n' + '\n'.join(items) + '\n'
                    
                    elif element.name == 'a':
                        href = element.get('href', '')
                        text = element.get_text(strip=True)
                        if href and text:
                            if not href.startswith(('http://', 'https://')):
                                href = urljoin(url, href)
                            return f"[{text}]({href})"
                        return text
                    
                    elif element.name == 'br':
                        return '\n'
                    
                    elif element.name in ['table']:
                        rows = []
                        # Handle table headers
                        headers = element.find_all('th')
                        if headers:
                            header_row = [h.get_text(strip=True) for h in headers]
                            rows.append('| ' + ' | '.join(header_row) + ' |')
                            rows.append('| ' + ' | '.join(['---'] * len(header_row)) + ' |')
                        
                        # Handle table rows
                        for tr in element.find_all('tr'):
                            cols = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                            if cols:  # Skip empty rows
                                rows.append('| ' + ' | '.join(cols) + ' |')
                        
                        return '\n' + '\n'.join(rows) + '\n'
                    
                    # Default handling for other elements
                    text = element.get_text(' ', strip=True)
                    return text if text else ''
                
                # Process the entire content
                markdown_content = []
                for element in content.children:
                    processed = process_element(element)
                    if processed:
                        markdown_content.append(processed)
                
                # Clean up multiple newlines and spaces
                final_content = '\n'.join(markdown_content)
                final_content = '\n'.join(line for line in final_content.splitlines() if line.strip())
                final_content = final_content.replace('\n\n\n\n', '\n\n')
                
                self.content_cache[url] = final_content
                return final_content
                
            except Exception as e:
                logging.error(f"Error fetching content from {url}: {e}")
                if attempt < self.retries - 1:
                    time.sleep(self.delay * (attempt + 1))
        
        return None

    def generate_toc_md(self, structure: List[Dict], level: int = 0) -> str:
        """Generate table of contents in markdown format."""
        toc = []
        for item in structure:
            indent = "  " * level
            toc.append(f"{indent}- [{item['title']}](#{item['title'].lower().replace(' ', '-')})")
            if item['children']:
                toc.append(self.generate_toc_md(item['children'], level + 1))
        return "\n".join(toc)

    def generate_markdown(self, structure: List[Dict], level: int = 1) -> str:
        """Generate structured markdown from navigation hierarchy."""
        content = []
        
        if self.generate_toc and level == 1:
            content.append("# Table of Contents\n")
            content.append(self.generate_toc_md(structure))
            content.append("\n---\n")
        
        for item in structure:
            header = '#' * level
            content.append(f"{header} {item['title']}\n")
            
            if item['url'] and item['url'] not in self.visited_urls:
                self.visited_urls.add(item['url'])
                page_content = self.fetch_content(item['url'])
                if page_content:
                    content.append(page_content + "\n")
                time.sleep(self.delay)
            
            if item['children']:
                content.append(self.generate_markdown(item['children'], level + 1))
            
            content.append("\n---\n")
        
        return "\n".join(content)

    def scrape(self):
        """Main scraping method."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}")
        ) as progress:
            try:
                progress.add_task("Extracting navigation structure...", total=None)
                self.nav_structure = self.extract_nav_structure()
                
                if not self.nav_structure:
                    raise NavigationExtractionError("Empty navigation structure")
                
                progress.add_task("Generating documentation...", total=None)
                content = self.generate_markdown(self.nav_structure)
                
                self.output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logging.info(f"Documentation saved to {self.output_file}")
                logging.info(f"Processed {len(self.visited_urls)} pages")
                
            except Exception as e:
                logging.error(f"Scraping failed: {str(e)}")
                raise