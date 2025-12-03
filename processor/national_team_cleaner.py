#!/usr/bin/env python3
"""
National Team Data Cleaner

Cleans national_teams.jsonl to remove:
- Coach records that were incorrectly parsed as national teams
- Non-team records (rivalries, articles about matches, etc.)
- Duplicate or invalid entries

Only keeps actual national team records (U-14, U-17, U-19, U-21, U-22, U-23, Senior team)
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import PARSED_DATA_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NationalTeamCleaner:
    """Clean national team data."""
    
    # Patterns that indicate a valid national team
    VALID_TEAM_PATTERNS = [
        r"đội tuyển",
        r"u-\d+\s+việt nam",
        r"việt nam\s*$",  # Ends with "Việt Nam"
        r"national team",
    ]
    
    # Keywords that indicate NOT a national team
    INVALID_KEYWORDS = [
        "cầu thủ",      # Player
        "huấn luyện",   # Coach
        "hlv",          # Coach abbreviation
        "kình địch",    # Rivalry
        "trận đấu",     # Match
        "giải đấu",     # Tournament
    ]
    
    # Known coach names to exclude
    KNOWN_COACHES = [
        "Dido",
        "Gong Oh-kyun",
        "Falko Götz",
        "Philippe Troussier",
        "Miura Toshiya",
        "Karl-Heinz Weigang",
        "Henrique Calisto",
        "Lee Young-jin",
        "Kim Han-Yoon",
        "Kim Han-yoon",
        "Colin Murphy",
        "Park Hang-seo",
        "Hoàng Anh Tuấn",
        "Nguyễn Hữu Thắng",
        "Mai Đức Chung",
        "Phan Thanh Hùng",
    ]
    
    # Valid Vietnamese national team wiki_ids (manually verified)
    VALID_TEAM_WIKI_IDS = {
        # Main teams
        21785,     # Đội tuyển bóng đá quốc gia Việt Nam (Senior Men)
        76837,     # Đội tuyển bóng đá nữ quốc gia Việt Nam (Senior Women)
        
        # Men's youth teams
        3231314,   # U-17 Việt Nam
        3432599,   # U-22 Việt Nam
        3391550,   # U-21 Việt Nam
        822084,    # U-23 Việt Nam
        3242453,   # U-14 Việt Nam
        2413043,   # U-19 Việt Nam
        
        # Women's youth teams
        3231654,   # U-14 nữ Việt Nam
        3241380,   # U-16 nữ Việt Nam
        3241445,   # U-19 nữ Việt Nam
        
        # Other teams
        3208748,   # Đội tuyển bóng đá bãi biển quốc gia Việt Nam
        3241103,   # Đội tuyển bóng đá trong nhà nữ quốc gia Việt Nam
    }
    
    def __init__(self):
        self.stats = {
            "total_loaded": 0,
            "valid_teams": 0,
            "removed_coaches": 0,
            "removed_other": 0,
            "added_from_raw": 0,
        }
    
    def load_data(self) -> List[Dict]:
        """Load national teams from JSONL file and supplement from raw data."""
        input_file = PARSED_DATA_DIR / "national_teams.jsonl"
        
        records = []
        existing_ids = set()
        
        # Load from parsed file
        if input_file.exists():
            with open(input_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            records.append(record)
                            existing_ids.add(record.get("wiki_id"))
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse line: {e}")
        
        logger.info(f"Loaded {len(records)} records from parsed file")
        
        # Supplement missing teams from raw data
        missing_ids = self.VALID_TEAM_WIKI_IDS - existing_ids
        if missing_ids:
            logger.info(f"Looking for {len(missing_ids)} missing teams in raw data...")
            for raw_file in RAW_DATA_DIR.glob("national_team_*.json"):
                try:
                    with open(raw_file, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                        page_id = raw_data.get("page_id")
                        if page_id in missing_ids:
                            # Create a minimal record from raw data
                            record = {
                                "wiki_id": page_id,
                                "wiki_url": raw_data.get("full_url", ""),
                                "wiki_title": raw_data.get("page_title", ""),
                                "name": self._extract_name_from_title(raw_data.get("page_title", "")),
                            }
                            records.append(record)
                            existing_ids.add(page_id)
                            self.stats["added_from_raw"] += 1
                            logger.info(f"Added from raw: {record['name']}")
                except Exception as e:
                    logger.debug(f"Error reading {raw_file}: {e}")
        
        self.stats["total_loaded"] = len(records)
        logger.info(f"Total records after supplement: {len(records)}")
        return records
    
    def _extract_name_from_title(self, title: str) -> str:
        """Extract team name from wiki title."""
        if not title:
            return ""
        
        # Remove common prefixes
        name = title.replace("Đội tuyển bóng đá ", "")
        name = name.replace("quốc gia ", "")
        name = name.replace("Việt Nam", "Việt Nam").strip()
        
        # Keep original if extraction fails
        if not name or len(name) < 3:
            return title
        
        return name
        
        self.stats["total_loaded"] = len(records)
        logger.info(f"Loaded {len(records)} records from {input_file}")
        return records
    
    def is_valid_national_team(self, record: Dict) -> bool:
        """
        Check if a record is a valid national team.
        
        Args:
            record: National team record
            
        Returns:
            True if valid national team, False otherwise
        """
        wiki_id = record.get("wiki_id")
        name = record.get("name", "").lower()
        wiki_title = record.get("wiki_title", "").lower()
        
        # Check if wiki_id is in known valid teams
        if wiki_id in self.VALID_TEAM_WIKI_IDS:
            return True
        
        # Check if name matches a known coach
        original_name = record.get("name", "")
        for coach in self.KNOWN_COACHES:
            if coach.lower() in original_name.lower():
                self.stats["removed_coaches"] += 1
                logger.debug(f"Removed coach: {original_name}")
                return False
        
        # Check for invalid keywords in title
        for keyword in self.INVALID_KEYWORDS:
            if keyword in wiki_title:
                self.stats["removed_other"] += 1
                logger.debug(f"Removed by keyword '{keyword}': {wiki_title}")
                return False
        
        # Check for valid team patterns
        combined_text = f"{name} {wiki_title}"
        for pattern in self.VALID_TEAM_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
        
        # If none of the patterns match, it's probably not a valid team
        self.stats["removed_other"] += 1
        logger.debug(f"Removed (no valid pattern): {record.get('name')}")
        return False
    
    def clean_record(self, record: Dict) -> Dict:
        """
        Clean a national team record.
        
        Args:
            record: Raw national team record
            
        Returns:
            Cleaned record
        """
        cleaned = record.copy()
        
        # Clean the name - remove wiki markup
        name = cleaned.get("name", "")
        # Remove {{nobold|...}} and similar markup
        name = re.sub(r"\{\{[^}]+\}\}", "", name).strip()
        cleaned["name"] = name
        
        # Extract team level (U-14, U-17, etc.)
        wiki_title = cleaned.get("wiki_title", "")
        name = cleaned.get("name", "")
        
        # Detect gender
        is_women = "nữ" in wiki_title.lower() or "nữ" in name.lower()
        cleaned["gender"] = "Women" if is_women else "Men"
        
        # Extract team level (U-14, U-17, etc.)
        level_match = re.search(r"U-(\d+)", wiki_title, re.IGNORECASE)
        if level_match:
            cleaned["team_level"] = f"U-{level_match.group(1)}"
        elif "bãi biển" in wiki_title.lower():
            cleaned["team_level"] = "Beach"
        elif "trong nhà" in wiki_title.lower() or "futsal" in wiki_title.lower():
            cleaned["team_level"] = "Futsal"
        else:
            # Senior team
            cleaned["team_level"] = "Senior"
        
        # Normalize name
        gender_suffix = " nữ" if is_women else ""
        if cleaned["team_level"] == "Senior":
            cleaned["canonical_name"] = f"Đội tuyển{gender_suffix} Việt Nam"
        elif cleaned["team_level"] in ["Beach", "Futsal"]:
            cleaned["canonical_name"] = f"Đội tuyển {cleaned['team_level']}{gender_suffix} Việt Nam"
        else:
            cleaned["canonical_name"] = f"Đội tuyển {cleaned['team_level']}{gender_suffix} Việt Nam"
        
        # Clean name for display
        if not cleaned["name"] or len(cleaned["name"]) < 3:
            cleaned["name"] = cleaned["canonical_name"]
        
        return cleaned
    
    def clean(self) -> List[Dict]:
        """
        Clean national team data.
        
        Returns:
            List of cleaned national team records
        """
        records = self.load_data()
        
        if not records:
            return []
        
        cleaned_records = []
        
        for record in records:
            if self.is_valid_national_team(record):
                cleaned = self.clean_record(record)
                cleaned_records.append(cleaned)
                self.stats["valid_teams"] += 1
        
        logger.info(f"Cleaned to {len(cleaned_records)} valid national teams")
        return cleaned_records
    
    def save(self, records: List[Dict], update_main: bool = True):
        """
        Save cleaned national team data.
        
        Args:
            records: Cleaned records
            update_main: Whether to update the main clean file
        """
        # Save to JSONL (parsed)
        output_jsonl = PARSED_DATA_DIR / "national_teams_clean.jsonl"
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(records)} records to {output_jsonl}")
        
        # Save to CSV (processed)
        import pandas as pd
        
        # Select columns for CSV
        csv_columns = [
            "wiki_id", "name", "canonical_name", "team_level", "gender",
            "wiki_title", "wiki_url"
        ]
        
        df = pd.DataFrame(records)
        
        # Ensure all columns exist
        for col in csv_columns:
            if col not in df.columns:
                df[col] = None
        
        df = df[csv_columns]
        
        output_csv = PROCESSED_DATA_DIR / "national_teams_vn_clean.csv"
        df.to_csv(output_csv, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} records to {output_csv}")
        
        if update_main:
            main_csv = PROCESSED_DATA_DIR / "national_teams_clean.csv"
            df.to_csv(main_csv, index=False, encoding="utf-8")
            logger.info(f"Updated main file: {main_csv}")
    
    def print_stats(self):
        """Print cleaning statistics."""
        print("\n" + "=" * 60)
        print("NATIONAL TEAM CLEANING STATISTICS")
        print("=" * 60)
        print(f"Total records loaded:    {self.stats['total_loaded']}")
        print(f"Added from raw data:     {self.stats['added_from_raw']}")
        print(f"Valid national teams:    {self.stats['valid_teams']}")
        print(f"Removed (coaches):       {self.stats['removed_coaches']}")
        print(f"Removed (other):         {self.stats['removed_other']}")
        print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean national team data")
    parser.add_argument(
        "--update-main",
        action="store_true",
        help="Update the main national_teams_clean.csv file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without saving"
    )
    
    args = parser.parse_args()
    
    cleaner = NationalTeamCleaner()
    records = cleaner.clean()
    
    if args.dry_run:
        print("\n=== Valid National Teams ===")
        for r in records:
            print(f"  - {r.get('name')} ({r.get('team_level')})")
    else:
        cleaner.save(records, update_main=args.update_main)
    
    cleaner.print_stats()


if __name__ == "__main__":
    main()
