"""
Text Collector for Vietnam Football Knowledge Graph Enrichment

This module fetches and collects text data from Wikipedia article bodies
and optional news sources for NLP-based knowledge graph enrichment.

Features:
- Fetches Wikipedia article body text (not just infobox)
- Cleans wiki markup, templates, and citations
- Caches raw texts to avoid re-scraping
- Tracks text versions for change detection
- Optional news article collection

Usage:
    python -m data_enrichment.text_collector --collect-wiki
    python -m data_enrichment.text_collector --collect-wiki --entity-type player
    python -m data_enrichment.text_collector --collect-news --source vnexpress
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple

import mwclient
import mwparserfromhell
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    API_DELAY_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    BASE_DIR,
    DATA_DIR,
    RAW_DATA_DIR,
    WIKI_PATH,
    WIKI_SITE,
    WIKI_USER_AGENT,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Output directories
TEXT_SOURCES_DIR = DATA_DIR / "text_sources"
WIKIPEDIA_TEXTS_DIR = TEXT_SOURCES_DIR / "wikipedia"
NEWS_TEXTS_DIR = TEXT_SOURCES_DIR / "news"
PROCESSED_TEXTS_DIR = DATA_DIR / "processed_texts"

# Sections to exclude from Wikipedia articles
EXCLUDED_SECTIONS = {
    "tham khảo",
    "liên kết ngoài",
    "chú thích",
    "xem thêm",
    "ghi chú",
    "nguồn",
    "tài liệu",
    "references",
    "external links",
    "see also",
    "notes",
    "further reading",
}

# Entity types to process
ENTITY_TYPES = ["player", "coach", "club", "national_team", "stadium", "competition"]


class TextCollector:
    """
    Collects text data from Wikipedia and news sources for NLP enrichment.
    
    Attributes:
        wiki_site: mwclient Site object for Vietnamese Wikipedia
        cache_enabled: Whether to skip already-downloaded texts
        delay: Delay between API calls in seconds
    """
    
    def __init__(
        self,
        delay: float = API_DELAY_SECONDS,
        cache_enabled: bool = True,
    ):
        """
        Initialize the text collector.
        
        Args:
            delay: Delay between API calls in seconds
            cache_enabled: Whether to skip already-downloaded texts
        """
        self.delay = delay
        self.cache_enabled = cache_enabled
        self.wiki_site: Optional[mwclient.Site] = None
        self._collected_ids: Set[int] = set()
        
        # Ensure output directories exist
        WIKIPEDIA_TEXTS_DIR.mkdir(parents=True, exist_ok=True)
        NEWS_TEXTS_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_TEXTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load cached IDs if caching enabled
        if self.cache_enabled:
            self._load_cached_ids()
    
    def _load_cached_ids(self) -> None:
        """Load page IDs from existing cached text files."""
        if not WIKIPEDIA_TEXTS_DIR.exists():
            return
        
        for file_path in WIKIPEDIA_TEXTS_DIR.glob("*.txt"):
            try:
                # Extract wiki_id from filename (format: entity_type_wiki_id.txt)
                parts = file_path.stem.rsplit("_", 1)
                if len(parts) == 2:
                    wiki_id = int(parts[1])
                    self._collected_ids.add(wiki_id)
            except (ValueError, IndexError):
                continue
        
        logger.info(f"Found {len(self._collected_ids)} cached text files")
    
    def _connect_to_wikipedia(self) -> mwclient.Site:
        """Connect to Vietnamese Wikipedia if not already connected."""
        if self.wiki_site is not None:
            return self.wiki_site
        
        logger.info(f"Connecting to {WIKI_SITE}...")
        
        for attempt in range(API_MAX_RETRIES):
            try:
                self.wiki_site = mwclient.Site(
                    WIKI_SITE,
                    path=WIKI_PATH,
                    clients_useragent=WIKI_USER_AGENT,
                )
                logger.info("Successfully connected to Wikipedia")
                return self.wiki_site
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < API_MAX_RETRIES - 1:
                    time.sleep(API_RETRY_DELAY)
                else:
                    raise ConnectionError(f"Failed to connect to {WIKI_SITE}") from e
    
    def _respect_rate_limit(self) -> None:
        """Sleep to respect rate limiting."""
        if self.delay > 0:
            time.sleep(self.delay)
    
    def _get_raw_data_files(
        self,
        entity_type: Optional[str] = None
    ) -> Generator[Path, None, None]:
        """
        Get paths to raw data JSON files.
        
        Args:
            entity_type: Filter by entity type (player, coach, club, etc.)
            
        Yields:
            Paths to raw data JSON files
        """
        if not RAW_DATA_DIR.exists():
            logger.warning(f"Raw data directory not found: {RAW_DATA_DIR}")
            return
        
        pattern = f"{entity_type}_*.json" if entity_type else "*.json"
        
        for file_path in RAW_DATA_DIR.glob(pattern):
            yield file_path
    
    def _extract_article_text(self, wikitext: str) -> str:
        """
        Extract clean text from Wikipedia wikitext.
        
        Removes:
        - Infoboxes and templates
        - Wiki markup (links, formatting)
        - Citations and references
        - Excluded sections
        
        Args:
            wikitext: Raw wikitext from Wikipedia
            
        Returns:
            Clean article text
        """
        try:
            # Parse wikitext
            parsed = mwparserfromhell.parse(wikitext)
            
            # Remove templates (infoboxes, citations, etc.)
            for template in parsed.filter_templates():
                try:
                    parsed.remove(template)
                except ValueError:
                    pass  # Template may have been removed as part of parent
            
            # Convert to text, keeping section structure
            text = str(parsed)
            
            # Remove wiki links but keep text: [[link|text]] -> text, [[link]] -> link
            text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)
            
            # Remove external links: [url text] -> text
            text = re.sub(r'\[https?://[^\s\]]+\s*([^\]]*)\]', r'\1', text)
            
            # Remove remaining URLs
            text = re.sub(r'https?://\S+', '', text)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            
            # Remove HTML entities
            text = re.sub(r'&[a-zA-Z]+;', ' ', text)
            text = re.sub(r'&#\d+;', ' ', text)
            
            # Remove wiki formatting
            text = re.sub(r"'''?", '', text)  # Bold/italic
            text = re.sub(r'={2,}', '\n', text)  # Headers to newlines
            
            # Remove file/image references
            text = re.sub(r'\[\[(?:File|Tập tin|Image|Hình):.*?\]\]', '', text, flags=re.IGNORECASE)
            
            # Remove category links
            text = re.sub(r'\[\[(?:Category|Thể loại):.*?\]\]', '', text, flags=re.IGNORECASE)
            
            # Remove remaining brackets
            text = re.sub(r'\{\{[^}]*\}\}', '', text)
            text = re.sub(r'\{[^}]*\}', '', text)
            
            # Remove reference tags
            text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
            text = re.sub(r'<ref[^>]*/>', '', text)
            
            # Clean up whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
            
            # Filter out excluded sections
            text = self._filter_excluded_sections(text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Error extracting article text: {e}")
            return ""
    
    def _filter_excluded_sections(self, text: str) -> str:
        """
        Remove excluded sections from article text.
        
        Args:
            text: Article text with section headers
            
        Returns:
            Text with excluded sections removed
        """
        lines = text.split('\n')
        filtered_lines = []
        skip_section = False
        current_section_level = 0
        
        for line in lines:
            # Check if this is a section header
            header_match = re.match(r'^(=+)\s*(.+?)\s*=+\s*$', line)
            
            if header_match:
                level = len(header_match.group(1))
                section_name = header_match.group(2).lower().strip()
                
                # Check if this section should be excluded
                if section_name in EXCLUDED_SECTIONS:
                    skip_section = True
                    current_section_level = level
                elif skip_section and level <= current_section_level:
                    # New section at same or higher level, stop skipping
                    skip_section = False
                    filtered_lines.append(line)
                elif not skip_section:
                    filtered_lines.append(line)
            elif not skip_section:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _compute_text_hash(self, text: str) -> str:
        """Compute MD5 hash of text for change detection."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def collect_wikipedia_texts(
        self,
        entity_type: Optional[str] = None,
        force_refresh: bool = False,
        max_articles: int = -1,
    ) -> Dict[str, int]:
        """
        Collect article body texts from already-crawled Wikipedia pages.
        
        Uses the raw JSON files from the base crawler to extract clean
        article text (excluding infobox data).
        
        Args:
            entity_type: Filter by entity type (player, coach, etc.)
            force_refresh: Re-collect even if cached
            max_articles: Maximum articles to process (-1 for unlimited)
            
        Returns:
            Statistics dict with counts
        """
        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped_cached": 0,
            "skipped_no_text": 0,
            "errors": 0,
        }
        
        # Get all raw data files
        files = list(self._get_raw_data_files(entity_type))
        stats["total_files"] = len(files)
        
        if not files:
            logger.warning("No raw data files found. Run the base crawler first.")
            return stats
        
        logger.info(f"Processing {len(files)} raw data files...")
        
        # Apply limit
        if max_articles > 0:
            files = files[:max_articles]
        
        for file_path in tqdm(files, desc="Collecting texts"):
            try:
                # Load raw data
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                wiki_id = raw_data.get("page_id")
                entity_type_from_file = raw_data.get("entity_type", "unknown")
                page_title = raw_data.get("page_title", "")
                wikitext = raw_data.get("wikitext", "")
                
                # Skip if cached and not forcing refresh
                if self.cache_enabled and not force_refresh and wiki_id in self._collected_ids:
                    stats["skipped_cached"] += 1
                    continue
                
                # Extract clean article text
                article_text = self._extract_article_text(wikitext)
                
                if not article_text or len(article_text) < 50:
                    stats["skipped_no_text"] += 1
                    continue
                
                # Save text file
                output_path = WIKIPEDIA_TEXTS_DIR / f"{entity_type_from_file}_{wiki_id}.txt"
                
                # Create metadata
                metadata = {
                    "wiki_id": wiki_id,
                    "entity_type": entity_type_from_file,
                    "page_title": page_title,
                    "text_hash": self._compute_text_hash(article_text),
                    "char_count": len(article_text),
                    "collected_at": datetime.utcnow().isoformat(),
                    "source": "wikipedia",
                }
                
                # Save text with metadata header
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- METADATA: {json.dumps(metadata)} -->\n\n")
                    f.write(article_text)
                
                self._collected_ids.add(wiki_id)
                stats["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["errors"] += 1
        
        logger.info(
            f"Collection complete: {stats['processed']} processed, "
            f"{stats['skipped_cached']} cached, {stats['errors']} errors"
        )
        
        return stats
    
    def fetch_wikipedia_text_by_title(
        self,
        page_title: str,
        entity_type: str = "unknown",
    ) -> Optional[Dict]:
        """
        Fetch article text directly from Wikipedia by page title.
        
        Useful for fetching texts that weren't in the original crawl.
        
        Args:
            page_title: Wikipedia page title
            entity_type: Entity type for classification
            
        Returns:
            Dict with text and metadata, or None if failed
        """
        site = self._connect_to_wikipedia()
        self._respect_rate_limit()
        
        try:
            page = site.pages[page_title]
            
            if not page.exists:
                logger.warning(f"Page does not exist: {page_title}")
                return None
            
            wikitext = page.text()
            article_text = self._extract_article_text(wikitext)
            
            if not article_text:
                return None
            
            return {
                "wiki_id": page.pageid,
                "entity_type": entity_type,
                "page_title": page_title,
                "text": article_text,
                "text_hash": self._compute_text_hash(article_text),
                "char_count": len(article_text),
                "collected_at": datetime.utcnow().isoformat(),
                "source": "wikipedia",
            }
            
        except Exception as e:
            logger.error(f"Error fetching '{page_title}': {e}")
            return None
    
    def list_collected_texts(
        self,
        entity_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        List all collected text files with metadata.
        
        Args:
            entity_type: Filter by entity type
            
        Returns:
            List of metadata dicts
        """
        results = []
        
        pattern = f"{entity_type}_*.txt" if entity_type else "*.txt"
        
        for file_path in WIKIPEDIA_TEXTS_DIR.glob(pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                
                # Parse metadata from first line
                metadata_match = re.match(r'<!-- METADATA: ({.*}) -->', first_line)
                if metadata_match:
                    metadata = json.loads(metadata_match.group(1))
                    metadata["file_path"] = str(file_path)
                    results.append(metadata)
                    
            except Exception as e:
                logger.warning(f"Error reading metadata from {file_path}: {e}")
        
        return results
    
    def get_text_content(self, file_path: Path) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Read a collected text file and return metadata and content.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Tuple of (metadata dict, text content)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from first line
            lines = content.split('\n', 2)
            metadata_match = re.match(r'<!-- METADATA: ({.*}) -->', lines[0])
            
            if metadata_match:
                metadata = json.loads(metadata_match.group(1))
                text = lines[2] if len(lines) > 2 else ""
                return metadata, text
            else:
                return None, content
                
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None, None
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about collected texts.
        
        Returns:
            Dict with collection statistics
        """
        stats = {
            "total_files": 0,
            "by_entity_type": {},
            "total_chars": 0,
            "avg_chars": 0,
        }
        
        texts = self.list_collected_texts()
        stats["total_files"] = len(texts)
        
        for text_meta in texts:
            entity_type = text_meta.get("entity_type", "unknown")
            char_count = text_meta.get("char_count", 0)
            
            if entity_type not in stats["by_entity_type"]:
                stats["by_entity_type"][entity_type] = {"count": 0, "chars": 0}
            
            stats["by_entity_type"][entity_type]["count"] += 1
            stats["by_entity_type"][entity_type]["chars"] += char_count
            stats["total_chars"] += char_count
        
        if stats["total_files"] > 0:
            stats["avg_chars"] = stats["total_chars"] // stats["total_files"]
        
        return stats


def main():
    """CLI entry point for text collector."""
    parser = argparse.ArgumentParser(
        description="Collect text data for Vietnam Football KG enrichment"
    )
    
    parser.add_argument(
        "--collect-wiki",
        action="store_true",
        help="Collect Wikipedia article body texts",
    )
    parser.add_argument(
        "--entity-type",
        type=str,
        choices=ENTITY_TYPES,
        help="Filter by entity type",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-collect even if cached",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=-1,
        help="Maximum articles to process (-1 for unlimited)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List collected texts",
    )
    
    args = parser.parse_args()
    
    collector = TextCollector()
    
    if args.stats:
        stats = collector.get_collection_stats()
        print("\n=== Text Collection Statistics ===")
        print(f"Total files: {stats['total_files']}")
        print(f"Total characters: {stats['total_chars']:,}")
        print(f"Average chars/file: {stats['avg_chars']:,}")
        print("\nBy entity type:")
        for entity_type, data in stats["by_entity_type"].items():
            print(f"  {entity_type}: {data['count']} files, {data['chars']:,} chars")
        return
    
    if args.list:
        texts = collector.list_collected_texts(args.entity_type)
        print(f"\n=== Collected Texts ({len(texts)} files) ===")
        for text_meta in texts[:20]:  # Show first 20
            print(f"  [{text_meta['entity_type']}] {text_meta['page_title']} ({text_meta['char_count']:,} chars)")
        if len(texts) > 20:
            print(f"  ... and {len(texts) - 20} more")
        return
    
    if args.collect_wiki:
        print("\n=== Collecting Wikipedia Article Texts ===")
        stats = collector.collect_wikipedia_texts(
            entity_type=args.entity_type,
            force_refresh=args.force_refresh,
            max_articles=args.max_articles,
        )
        print(f"\nCollection complete:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Skipped (cached): {stats['skipped_cached']}")
        print(f"  Skipped (no text): {stats['skipped_no_text']}")
        print(f"  Errors: {stats['errors']}")
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
