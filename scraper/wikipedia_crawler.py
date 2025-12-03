"""
Wikipedia Crawler for Vietnamese Football Knowledge Graph

This module fetches page data from vi.wikipedia.org for Vietnamese football
players, coaches, clubs, and national teams.

Features:
- Fetches pages from specified categories using MediaWiki API
- Rate limiting to respect Wikipedia servers
- Caching to skip already-downloaded pages
- Progress bar with tqdm
- Saves raw data as JSON files

Usage:
    python -m scraper.wikipedia_crawler --fetch-all
    python -m scraper.wikipedia_crawler --category "Cầu thủ bóng đá Việt Nam"
    python -m scraper.wikipedia_crawler --fetch-all --no-cache
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple

import mwclient
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    API_DELAY_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    CATEGORY_RECURSION_DEPTH,
    RAW_DATA_DIR,
    WIKI_CATEGORIES,
    WIKI_PATH,
    WIKI_SITE,
    WIKI_USER_AGENT,
    get_raw_file_path,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WikipediaCrawler:
    """
    Crawler for fetching Vietnamese Wikipedia pages about football.
    
    Attributes:
        site: mwclient Site object for vi.wikipedia.org
        delay: Delay between API calls in seconds
        cache_enabled: Whether to skip already-downloaded pages
    """
    
    def __init__(
        self,
        delay: float = API_DELAY_SECONDS,
        cache_enabled: bool = True,
    ):
        """
        Initialize the crawler.
        
        Args:
            delay: Delay between API calls in seconds
            cache_enabled: Whether to skip already-downloaded pages
        """
        self.delay = delay
        self.cache_enabled = cache_enabled
        self.site = self._connect_to_wikipedia()
        self._downloaded_pages: Set[int] = set()
        
        # Load existing page IDs if caching is enabled
        if self.cache_enabled:
            self._load_cached_page_ids()
    
    def _connect_to_wikipedia(self) -> mwclient.Site:
        """
        Connect to Vietnamese Wikipedia.
        
        Returns:
            mwclient.Site object
        """
        logger.info(f"Connecting to {WIKI_SITE}...")
        
        for attempt in range(API_MAX_RETRIES):
            try:
                site = mwclient.Site(
                    WIKI_SITE,
                    path=WIKI_PATH,
                    clients_useragent=WIKI_USER_AGENT,
                )
                logger.info("Successfully connected to Wikipedia")
                return site
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < API_MAX_RETRIES - 1:
                    time.sleep(API_RETRY_DELAY)
                else:
                    raise ConnectionError(f"Failed to connect to {WIKI_SITE}") from e
    
    def _load_cached_page_ids(self) -> None:
        """Load page IDs from existing cached files."""
        if not RAW_DATA_DIR.exists():
            return
        
        for file_path in RAW_DATA_DIR.glob("*.json"):
            try:
                # Extract page_id from filename (format: entity_type_page_id.json)
                parts = file_path.stem.rsplit("_", 1)
                if len(parts) == 2:
                    page_id = int(parts[1])
                    self._downloaded_pages.add(page_id)
            except (ValueError, IndexError):
                continue
        
        logger.info(f"Found {len(self._downloaded_pages)} cached pages")
    
    def _respect_rate_limit(self) -> None:
        """Sleep to respect rate limiting."""
        if self.delay > 0:
            time.sleep(self.delay)
    
    def get_category_members(
        self,
        category_name: str,
        entity_type: str,
        depth: int = 0,
    ) -> Generator[Tuple[str, str, int], None, None]:
        """
        Get all pages in a category (and optionally subcategories).
        
        Args:
            category_name: Name of the Wikipedia category
            entity_type: Type of entity (player, coach, club, national_team)
            depth: Current recursion depth for subcategories
            
        Yields:
            Tuples of (page_title, entity_type, page_id)
        """
        logger.info(f"Fetching category: {category_name}")
        
        try:
            category = self.site.categories[category_name]
        except Exception as e:
            logger.error(f"Failed to access category '{category_name}': {e}")
            return
        
        seen_pages: Set[int] = set()
        
        for member in category.members():
            self._respect_rate_limit()
            
            # Skip if already seen in this session
            page_id = member.pageid
            if page_id in seen_pages:
                continue
            seen_pages.add(page_id)
            
            # Handle subcategories
            if member.namespace == 14:  # Category namespace
                if depth < CATEGORY_RECURSION_DEPTH:
                    subcat_name = member.name.replace("Category:", "").replace("Thể loại:", "")
                    yield from self.get_category_members(
                        subcat_name,
                        entity_type,
                        depth + 1,
                    )
            # Handle regular pages (namespace 0 = main articles)
            elif member.namespace == 0:
                yield (member.name, entity_type, page_id)
    
    def fetch_page_data(
        self,
        page_title: str,
        entity_type: str,
    ) -> Optional[Dict]:
        """
        Fetch full page data including wikitext.
        
        Args:
            page_title: Title of the Wikipedia page
            entity_type: Type of entity (player, coach, club, national_team)
            
        Returns:
            Dictionary with page data, or None if failed
        """
        for attempt in range(API_MAX_RETRIES):
            try:
                page = self.site.pages[page_title]
                
                if not page.exists:
                    logger.warning(f"Page does not exist: {page_title}")
                    return None
                
                # Get page content
                wikitext = page.text()
                
                # Build page data
                page_data = {
                    "page_id": page.pageid,
                    "page_title": page_title,
                    "entity_type": entity_type,
                    "full_url": f"https://{WIKI_SITE}/wiki/{page_title.replace(' ', '_')}",
                    "wikitext": wikitext,
                    "last_revision_id": page.revision,
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                
                return page_data
                
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for '{page_title}': {e}"
                )
                if attempt < API_MAX_RETRIES - 1:
                    time.sleep(API_RETRY_DELAY)
                else:
                    logger.error(f"Failed to fetch page '{page_title}' after {API_MAX_RETRIES} attempts")
                    return None
        
        return None
    
    def save_page_data(self, page_data: Dict) -> Path:
        """
        Save page data to JSON file.
        
        Args:
            page_data: Dictionary with page data
            
        Returns:
            Path to the saved file
        """
        file_path = get_raw_file_path(
            page_data["entity_type"],
            page_data["page_id"],
        )
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def fetch_category(
        self,
        category_name: str,
        entity_type: str,
    ) -> Dict[str, int]:
        """
        Fetch all pages from a category and save them.
        
        Args:
            category_name: Name of the Wikipedia category
            entity_type: Type of entity
            
        Returns:
            Dictionary with stats (total, fetched, cached, failed)
        """
        stats = {
            "total": 0,
            "fetched": 0,
            "cached": 0,
            "failed": 0,
        }
        
        # First, collect all page titles
        logger.info(f"Collecting pages from category: {category_name}")
        pages_to_fetch: List[Tuple[str, str, int]] = []
        
        for page_info in self.get_category_members(category_name, entity_type):
            page_title, etype, page_id = page_info
            stats["total"] += 1
            
            # Check cache
            if self.cache_enabled and page_id in self._downloaded_pages:
                stats["cached"] += 1
                continue
            
            pages_to_fetch.append(page_info)
        
        logger.info(
            f"Found {stats['total']} pages, "
            f"{stats['cached']} cached, "
            f"{len(pages_to_fetch)} to fetch"
        )
        
        # Fetch pages with progress bar
        if pages_to_fetch:
            for page_title, etype, page_id in tqdm(
                pages_to_fetch,
                desc=f"Fetching {entity_type}",
                unit="page",
            ):
                self._respect_rate_limit()
                
                page_data = self.fetch_page_data(page_title, etype)
                
                if page_data:
                    self.save_page_data(page_data)
                    self._downloaded_pages.add(page_id)
                    stats["fetched"] += 1
                else:
                    stats["failed"] += 1
        
        return stats
    
    def fetch_all_categories(self) -> Dict[str, Dict[str, int]]:
        """
        Fetch all pages from all configured categories.
        
        Returns:
            Dictionary mapping category names to their stats
        """
        all_stats = {}
        
        logger.info(f"Starting to fetch {len(WIKI_CATEGORIES)} categories...")
        
        for category_name, entity_type in WIKI_CATEGORIES.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing category: {category_name} ({entity_type})")
            logger.info(f"{'='*60}")
            
            stats = self.fetch_category(category_name, entity_type)
            all_stats[category_name] = stats
            
            logger.info(
                f"Category '{category_name}' complete: "
                f"{stats['fetched']} fetched, "
                f"{stats['cached']} cached, "
                f"{stats['failed']} failed"
            )
        
        # Print summary
        self._print_summary(all_stats)
        
        return all_stats
    
    def _print_summary(self, all_stats: Dict[str, Dict[str, int]]) -> None:
        """Print a summary of all fetched categories."""
        print("\n" + "=" * 60)
        print("CRAWL SUMMARY")
        print("=" * 60)
        
        total_stats = {"total": 0, "fetched": 0, "cached": 0, "failed": 0}
        
        for category_name, stats in all_stats.items():
            print(f"\n{category_name}:")
            print(f"  Total: {stats['total']}")
            print(f"  Fetched: {stats['fetched']}")
            print(f"  Cached: {stats['cached']}")
            print(f"  Failed: {stats['failed']}")
            
            for key in total_stats:
                total_stats[key] += stats[key]
        
        print("\n" + "-" * 60)
        print("TOTAL:")
        print(f"  Total pages: {total_stats['total']}")
        print(f"  Newly fetched: {total_stats['fetched']}")
        print(f"  From cache: {total_stats['cached']}")
        print(f"  Failed: {total_stats['failed']}")
        print("=" * 60)


def main():
    """Main entry point for the crawler CLI."""
    parser = argparse.ArgumentParser(
        description="Fetch Vietnamese football pages from Wikipedia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Fetch all categories:
    python -m scraper.wikipedia_crawler --fetch-all
    
  Fetch a specific category:
    python -m scraper.wikipedia_crawler --category "Cầu thủ bóng đá Việt Nam" --entity-type player
    
  Fetch without cache (re-download everything):
    python -m scraper.wikipedia_crawler --fetch-all --no-cache
    
  Custom delay between requests:
    python -m scraper.wikipedia_crawler --fetch-all --delay 2.0
        """,
    )
    
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="Fetch all pages from all configured categories",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Fetch a specific category by name",
    )
    parser.add_argument(
        "--entity-type",
        type=str,
        choices=["player", "coach", "club", "national_team"],
        help="Entity type for the category (required with --category)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (re-download all pages)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=API_DELAY_SECONDS,
        help=f"Delay between API calls in seconds (default: {API_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List all configured categories and exit",
    )
    
    args = parser.parse_args()
    
    # List categories mode
    if args.list_categories:
        print("Configured categories:")
        for category_name, entity_type in WIKI_CATEGORIES.items():
            print(f"  - {category_name} ({entity_type})")
        return
    
    # Validate arguments
    if not args.fetch_all and not args.category:
        parser.error("Either --fetch-all or --category must be specified")
    
    if args.category and not args.entity_type:
        parser.error("--entity-type is required when using --category")
    
    # Create crawler
    crawler = WikipediaCrawler(
        delay=args.delay,
        cache_enabled=not args.no_cache,
    )
    
    # Run crawler
    if args.fetch_all:
        crawler.fetch_all_categories()
    elif args.category:
        stats = crawler.fetch_category(args.category, args.entity_type)
        print(f"\nCompleted: {stats['fetched']} fetched, {stats['cached']} cached, {stats['failed']} failed")


if __name__ == "__main__":
    main()
