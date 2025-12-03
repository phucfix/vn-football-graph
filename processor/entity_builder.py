"""
Entity Builder for Vietnamese Football Knowledge Graph

This module normalizes and deduplicates parsed entities from JSONL files
into clean CSV files ready for Neo4j import.

Features:
- Loads JSONL files into Pandas DataFrames
- Removes rows with missing critical fields
- Deduplicates entities based on name + other fields
- Creates canonical names for duplicates
- Builds reference tables for positions and nationalities
- Outputs clean CSV files

Usage:
    python -m processor.entity_builder --normalize-all
    python -m processor.entity_builder --entity-type player
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    DEDUP_FIELDS,
    ENTITY_TYPES,
    POSITION_MAPPINGS,
    PROCESSED_DATA_DIR,
    REQUIRED_FIELDS,
    get_parsed_file_path,
    get_processed_file_path,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EntityBuilder:
    """
    Builder for normalizing and deduplicating entities.
    """
    
    def __init__(self):
        """Initialize the entity builder."""
        self.stats = {}
        self.positions_set: Set[str] = set()
        self.nationalities_set: Set[str] = set()
    
    def load_jsonl(self, entity_type: str) -> pd.DataFrame:
        """
        Load a JSONL file into a DataFrame.
        
        Args:
            entity_type: Type of entity to load
            
        Returns:
            DataFrame with entity data
        """
        file_path = get_parsed_file_path(entity_type)
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return pd.DataFrame()
        
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON line: {e}")
        
        logger.info(f"Loaded {len(records)} {entity_type}s from {file_path}")
        return pd.DataFrame(records)
    
    def remove_missing_required(
        self,
        df: pd.DataFrame,
        entity_type: str,
    ) -> pd.DataFrame:
        """
        Remove rows missing required fields.
        
        Args:
            df: Input DataFrame
            entity_type: Type of entity
            
        Returns:
            Filtered DataFrame
        """
        required = REQUIRED_FIELDS.get(entity_type, [])
        
        if not required:
            return df
        
        original_count = len(df)
        
        # Check which required fields exist in the DataFrame
        existing_required = [f for f in required if f in df.columns]
        
        if not existing_required:
            return df
        
        # Remove rows where any required field is null or empty
        for field in existing_required:
            df = df[df[field].notna()]
            df = df[df[field].astype(str).str.strip() != '']
        
        removed_count = original_count - len(df)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} rows with missing required fields")
        
        return df
    
    def deduplicate(
        self,
        df: pd.DataFrame,
        entity_type: str,
    ) -> pd.DataFrame:
        """
        Deduplicate entities based on configured fields.
        
        Args:
            df: Input DataFrame
            entity_type: Type of entity
            
        Returns:
            Deduplicated DataFrame
        """
        dedup_fields = DEDUP_FIELDS.get(entity_type, ["name"])
        
        # Only use fields that exist in the DataFrame
        existing_dedup = [f for f in dedup_fields if f in df.columns]
        
        if not existing_dedup:
            return df
        
        original_count = len(df)
        
        # For deduplication, sort by wiki_id (keep oldest) and drop duplicates
        if "wiki_id" in df.columns:
            df = df.sort_values("wiki_id")
        
        df = df.drop_duplicates(subset=existing_dedup, keep="first")
        
        removed_count = original_count - len(df)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate rows based on {existing_dedup}")
        
        return df
    
    def create_canonical_names(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Create canonical names for entities with duplicate names.
        
        Adds a suffix with birth year if multiple entities have the same name.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with canonical_name column
        """
        if "name" not in df.columns:
            df["canonical_name"] = df.index.astype(str)
            return df
        
        # Count name occurrences
        name_counts = df["name"].value_counts()
        duplicate_names = set(name_counts[name_counts > 1].index)
        
        def make_canonical(row):
            name = row.get("name", "")
            if name in duplicate_names:
                # Try to add birth year
                dob = row.get("date_of_birth", "")
                if dob and isinstance(dob, str):
                    year_match = re.search(r"(\d{4})", dob)
                    if year_match:
                        return f"{name} ({year_match.group(1)})"
                # Fallback to wiki_id
                wiki_id = row.get("wiki_id", "")
                if wiki_id:
                    return f"{name} (#{wiki_id})"
            return name
        
        df["canonical_name"] = df.apply(make_canonical, axis=1)
        
        # Check for any remaining duplicates
        remaining_dups = df["canonical_name"].duplicated().sum()
        if remaining_dups > 0:
            logger.warning(f"{remaining_dups} canonical names still duplicated")
        
        return df
    
    def normalize_positions(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Normalize position field and collect unique positions.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized positions
        """
        if "position" not in df.columns:
            return df
        
        def normalize_pos(pos):
            if pd.isna(pos) or not pos:
                return None
            
            pos_str = str(pos).lower().strip()
            
            # Check direct mapping
            if pos_str in POSITION_MAPPINGS:
                return POSITION_MAPPINGS[pos_str]
            
            # Check partial matches
            for key, code in POSITION_MAPPINGS.items():
                if key in pos_str:
                    return code
            
            # Fallback
            return pos_str.upper()[:3] if pos_str else None
        
        df["position_normalized"] = df["position"].apply(normalize_pos)
        
        # Collect unique positions
        unique_positions = df["position_normalized"].dropna().unique()
        self.positions_set.update(unique_positions)
        
        return df
    
    def normalize_nationalities(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Normalize nationality field and collect unique nationalities.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized nationalities
        """
        if "nationality" not in df.columns:
            return df
        
        # Common nationality mappings
        nationality_map = {
            "việt nam": "Vietnam",
            "vietnam": "Vietnam",
            "vn": "Vietnam",
            "brazil": "Brazil",
            "brasil": "Brazil",
            "japan": "Japan",
            "nhật bản": "Japan",
            "south korea": "South Korea",
            "korea republic": "South Korea",
            "hàn quốc": "South Korea",
            "thailand": "Thailand",
            "thái lan": "Thailand",
        }
        
        def normalize_nat(nat):
            if pd.isna(nat) or not nat:
                return "Vietnam"  # Default for Vietnamese football
            
            nat_str = str(nat).lower().strip()
            
            # Check mapping
            if nat_str in nationality_map:
                return nationality_map[nat_str]
            
            # Title case
            return nat.strip().title()
        
        df["nationality_normalized"] = df["nationality"].apply(normalize_nat)
        
        # Collect unique nationalities
        unique_nationalities = df["nationality_normalized"].dropna().unique()
        self.nationalities_set.update(unique_nationalities)
        
        return df
    
    def flatten_career_history(
        self,
        df: pd.DataFrame,
        history_column: str,
    ) -> pd.DataFrame:
        """
        Flatten nested career history into separate columns or keep as JSON.
        
        For now, we keep it as JSON string for the main table.
        The relationship builder will process these lists.
        
        Args:
            df: Input DataFrame
            history_column: Name of the career history column
            
        Returns:
            DataFrame with JSON-stringified history
        """
        if history_column not in df.columns:
            return df
        
        def to_json_str(val):
            # Handle None/NaN - check for scalar NaN first
            if val is None:
                return "[]"
            try:
                if pd.isna(val):
                    return "[]"
            except (ValueError, TypeError):
                # pd.isna fails for arrays/lists, which means it's not NaN
                pass
            if isinstance(val, list):
                return json.dumps(val, ensure_ascii=False)
            if isinstance(val, str):
                return val
            return str(val)
        
        df[history_column] = df[history_column].apply(to_json_str)
        
        return df
    
    def process_players(self) -> pd.DataFrame:
        """
        Process player entities.
        
        Returns:
            Cleaned DataFrame of players
        """
        df = self.load_jsonl("player")
        
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Pipeline
        df = self.remove_missing_required(df, "player")
        df = self.deduplicate(df, "player")
        df = self.create_canonical_names(df)
        df = self.normalize_positions(df)
        df = self.normalize_nationalities(df)
        
        # Flatten career histories
        df = self.flatten_career_history(df, "clubs_history")
        df = self.flatten_career_history(df, "national_team_history")
        
        # Select and order columns for output
        output_columns = [
            "wiki_id", "name", "canonical_name", "full_name",
            "date_of_birth", "place_of_birth",
            "nationality", "nationality_normalized",
            "position", "position_normalized",
            "height", "current_club",
            "clubs_history", "national_team_history",
            "wiki_url", "wiki_title",
        ]
        
        # Only include columns that exist
        output_columns = [c for c in output_columns if c in df.columns]
        df = df[output_columns]
        
        self.stats["player"] = {
            "original": original_count,
            "final": len(df),
            "deduped": original_count - len(df),
        }
        
        return df
    
    def process_coaches(self) -> pd.DataFrame:
        """
        Process coach entities.
        
        Returns:
            Cleaned DataFrame of coaches
        """
        df = self.load_jsonl("coach")
        
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Pipeline
        df = self.remove_missing_required(df, "coach")
        df = self.deduplicate(df, "coach")
        df = self.create_canonical_names(df)
        df = self.normalize_nationalities(df)
        
        # Flatten career histories
        df = self.flatten_career_history(df, "clubs_managed")
        df = self.flatten_career_history(df, "national_teams_managed")
        
        # Select columns
        output_columns = [
            "wiki_id", "name", "canonical_name", "full_name",
            "date_of_birth", "nationality", "nationality_normalized",
            "clubs_managed", "national_teams_managed",
            "wiki_url", "wiki_title",
        ]
        output_columns = [c for c in output_columns if c in df.columns]
        df = df[output_columns]
        
        self.stats["coach"] = {
            "original": original_count,
            "final": len(df),
            "deduped": original_count - len(df),
        }
        
        return df
    
    def process_clubs(self) -> pd.DataFrame:
        """
        Process club entities.
        
        Returns:
            Cleaned DataFrame of clubs
        """
        df = self.load_jsonl("club")
        
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Pipeline
        df = self.remove_missing_required(df, "club")
        df = self.deduplicate(df, "club")
        df = self.create_canonical_names(df)
        
        # Select columns
        output_columns = [
            "wiki_id", "name", "canonical_name", "full_name",
            "founded", "ground", "capacity",
            "chairman", "manager", "league", "country",
            "wiki_url", "wiki_title",
        ]
        output_columns = [c for c in output_columns if c in df.columns]
        df = df[output_columns]
        
        self.stats["club"] = {
            "original": original_count,
            "final": len(df),
            "deduped": original_count - len(df),
        }
        
        return df
    
    def process_national_teams(self) -> pd.DataFrame:
        """
        Process national team entities.
        
        Returns:
            Cleaned DataFrame of national teams
        """
        df = self.load_jsonl("national_team")
        
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Pipeline
        df = self.remove_missing_required(df, "national_team")
        df = self.deduplicate(df, "national_team")
        df = self.create_canonical_names(df)
        
        # Select columns
        output_columns = [
            "wiki_id", "name", "canonical_name",
            "country_code", "level", "manager", "confederation",
            "wiki_url", "wiki_title",
        ]
        output_columns = [c for c in output_columns if c in df.columns]
        df = df[output_columns]
        
        self.stats["national_team"] = {
            "original": original_count,
            "final": len(df),
            "deduped": original_count - len(df),
        }
        
        return df
    
    def process_stadiums(self) -> pd.DataFrame:
        """
        Process stadium entities.
        
        Returns:
            Cleaned DataFrame of stadiums
        """
        df = self.load_jsonl("stadium")
        
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Pipeline
        df = self.remove_missing_required(df, "stadium")
        df = self.deduplicate(df, "stadium")
        df = self.create_canonical_names(df)
        
        # Extract capacity as integer if possible
        def parse_capacity(cap):
            if pd.isna(cap) or not cap:
                return None
            cap_str = str(cap)
            # Extract numbers from string like "40,000" or "40000 chỗ"
            import re
            numbers = re.findall(r'[\d,\.]+', cap_str.replace('.', '').replace(',', ''))
            if numbers:
                try:
                    return int(numbers[0])
                except ValueError:
                    return None
            return None
        
        if 'capacity' in df.columns:
            df['capacity_int'] = df['capacity'].apply(parse_capacity)
        
        # Select columns
        output_columns = [
            "wiki_id", "name", "canonical_name",
            "location", "capacity", "capacity_int",
            "surface", "opened", "owner", "home_teams",
            "wiki_url", "wiki_title",
        ]
        output_columns = [c for c in output_columns if c in df.columns]
        df = df[output_columns]
        
        self.stats["stadium"] = {
            "original": original_count,
            "final": len(df),
            "deduped": original_count - len(df),
        }
        
        return df
    
    def process_competitions(self) -> pd.DataFrame:
        """
        Process competition entities.
        
        Returns:
            Cleaned DataFrame of competitions
        """
        df = self.load_jsonl("competition")
        
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Pipeline
        df = self.remove_missing_required(df, "competition")
        df = self.deduplicate(df, "competition")
        df = self.create_canonical_names(df)
        
        # Extract year from name (e.g., "V.League 1 – 2022" -> 2022)
        def extract_year(name):
            if pd.isna(name) or not name:
                return None
            import re
            years = re.findall(r'(19\d{2}|20\d{2})', str(name))
            if years:
                return int(years[-1])  # Take the last year found
            return None
        
        df['season_year'] = df['name'].apply(extract_year)
        
        # Determine competition type from name
        def determine_type(row):
            name = str(row.get('name', '')).lower()
            comp_type = row.get('competition_type')
            if comp_type and not pd.isna(comp_type):
                return comp_type
            if 'cup' in name or 'cúp' in name:
                return 'cup'
            if 'league' in name or 'v-league' in name or 'vô địch' in name:
                return 'league'
            if 'hạng nhất' in name or 'v.league 2' in name:
                return 'second_division'
            if 'nữ' in name or 'women' in name:
                return 'women'
            if 'u21' in name or 'u23' in name or 'trẻ' in name:
                return 'youth'
            return 'other'
        
        df['competition_type'] = df.apply(determine_type, axis=1)
        
        # Select columns
        output_columns = [
            "wiki_id", "name", "canonical_name",
            "competition_type", "season_year",
            "country", "founded", "teams", "level",
            "current_champion", "most_titles",
            "wiki_url", "wiki_title",
        ]
        output_columns = [c for c in output_columns if c in df.columns]
        df = df[output_columns]
        
        self.stats["competition"] = {
            "original": original_count,
            "final": len(df),
            "deduped": original_count - len(df),
        }
        
        return df
    
    def save_dataframe(
        self,
        df: pd.DataFrame,
        entity_type: str,
    ) -> Path:
        """
        Save DataFrame to CSV file.
        
        Args:
            df: DataFrame to save
            entity_type: Type of entity
            
        Returns:
            Path to saved file
        """
        output_path = get_processed_file_path(entity_type)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} {entity_type}s to {output_path}")
        
        return output_path
    
    def create_positions_reference(self) -> pd.DataFrame:
        """
        Create reference table for positions.
        
        Returns:
            DataFrame with position codes and names
        """
        # Standard position definitions
        position_definitions = {
            "GK": "Goalkeeper",
            "CB": "Centre-Back",
            "LB": "Left-Back",
            "RB": "Right-Back",
            "FB": "Full-Back",
            "DF": "Defender",
            "DM": "Defensive Midfielder",
            "CM": "Central Midfielder",
            "AM": "Attacking Midfielder",
            "LM": "Left Midfielder",
            "RM": "Right Midfielder",
            "WM": "Winger",
            "MF": "Midfielder",
            "CF": "Centre-Forward",
            "ST": "Striker",
            "WF": "Wing Forward",
            "FW": "Forward",
        }
        
        # Include positions found in data
        all_positions = set(position_definitions.keys())
        all_positions.update(self.positions_set)
        
        records = []
        for pos_code in sorted(all_positions):
            records.append({
                "position_id": pos_code,
                "position_code": pos_code,
                "position_name": position_definitions.get(pos_code, pos_code),
            })
        
        df = pd.DataFrame(records)
        
        # Save
        output_path = PROCESSED_DATA_DIR / "positions_reference.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} positions to {output_path}")
        
        return df
    
    def create_nationalities_reference(self) -> pd.DataFrame:
        """
        Create reference table for nationalities.
        
        Returns:
            DataFrame with nationality names and codes
        """
        # Standard country codes
        country_codes = {
            "Vietnam": "VN",
            "Brazil": "BR",
            "Japan": "JP",
            "South Korea": "KR",
            "Thailand": "TH",
            "Indonesia": "ID",
            "Malaysia": "MY",
            "Singapore": "SG",
            "Philippines": "PH",
            "Australia": "AU",
            "France": "FR",
            "Germany": "DE",
            "England": "GB",
            "Spain": "ES",
            "Italy": "IT",
            "Argentina": "AR",
            "Portugal": "PT",
            "Netherlands": "NL",
        }
        
        # Include nationalities found in data
        all_nationalities = set(country_codes.keys())
        all_nationalities.update(self.nationalities_set)
        
        records = []
        for i, nat in enumerate(sorted(all_nationalities), 1):
            records.append({
                "nationality_id": i,
                "nationality_name": nat,
                "country_code": country_codes.get(nat, nat[:2].upper()),
            })
        
        df = pd.DataFrame(records)
        
        # Save
        output_path = PROCESSED_DATA_DIR / "nationalities_reference.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} nationalities to {output_path}")
        
        return df
    
    def normalize_all(self) -> Dict[str, pd.DataFrame]:
        """
        Process all entity types.
        
        Returns:
            Dictionary mapping entity type to DataFrame
        """
        results = {}
        
        # Process each entity type
        processors = {
            "player": self.process_players,
            "coach": self.process_coaches,
            "club": self.process_clubs,
            "national_team": self.process_national_teams,
            "stadium": self.process_stadiums,
            "competition": self.process_competitions,
        }
        
        for entity_type, processor in processors.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {entity_type}")
            logger.info(f"{'='*60}")
            
            df = processor()
            
            if not df.empty:
                self.save_dataframe(df, entity_type)
                results[entity_type] = df
        
        # Create reference tables
        logger.info(f"\n{'='*60}")
        logger.info("Creating reference tables")
        logger.info(f"{'='*60}")
        
        self.create_positions_reference()
        self.create_nationalities_reference()
        
        # Print summary
        self._print_summary()
        
        return results
    
    def _print_summary(self) -> None:
        """Print processing summary."""
        print("\n" + "=" * 60)
        print("NORMALIZATION SUMMARY")
        print("=" * 60)
        
        for entity_type, stats in self.stats.items():
            print(f"\n{entity_type}:")
            print(f"  Original: {stats['original']}")
            print(f"  Final: {stats['final']}")
            print(f"  Deduped: {stats['deduped']}")
        
        print("\n" + "-" * 60)
        print(f"Positions found: {len(self.positions_set)}")
        print(f"Nationalities found: {len(self.nationalities_set)}")
        print("=" * 60)


def main():
    """Main entry point for the entity builder CLI."""
    parser = argparse.ArgumentParser(
        description="Normalize and deduplicate parsed entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Normalize all entity types:
    python -m processor.entity_builder --normalize-all
    
  Normalize only players:
    python -m processor.entity_builder --entity-type player
        """,
    )
    
    parser.add_argument(
        "--normalize-all",
        action="store_true",
        help="Normalize all entity types",
    )
    parser.add_argument(
        "--entity-type",
        type=str,
        choices=ENTITY_TYPES,
        help="Normalize only a specific entity type",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.normalize_all and not args.entity_type:
        parser.error("Must specify --normalize-all or --entity-type")
    
    # Create builder
    builder = EntityBuilder()
    
    # Run builder
    if args.normalize_all:
        builder.normalize_all()
    elif args.entity_type:
        processors = {
            "player": builder.process_players,
            "coach": builder.process_coaches,
            "club": builder.process_clubs,
            "national_team": builder.process_national_teams,
        }
        
        df = processors[args.entity_type]()
        if not df.empty:
            builder.save_dataframe(df, args.entity_type)
            print(f"\nNormalized {len(df)} {args.entity_type}s")
        else:
            print(f"\nNo data found for {args.entity_type}")


if __name__ == "__main__":
    main()
