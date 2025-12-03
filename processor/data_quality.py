"""
Data Quality Improvements for Vietnamese Football Knowledge Graph

This module provides functions to:
- Fix concatenated names (foreign names merged with Vietnamese names)
- Extract provinces/cities from place_of_birth
- Add birth_year column
- Standardize club names
- Clean and improve data quality

Usage:
    python -m processor.data_quality --improve-all
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    PROCESSED_DATA_DIR,
    EDGES_DATA_DIR,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# VIETNAMESE PROVINCES/CITIES
# =============================================================================

VIETNAM_PROVINCES = {
    # Major cities
    "Hà Nội": {"type": "city", "region": "North"},
    "Thành phố Hồ Chí Minh": {"type": "city", "region": "South"},
    "TP. Hồ Chí Minh": {"type": "city", "region": "South"},
    "TP.HCM": {"type": "city", "region": "South"},
    "Đà Nẵng": {"type": "city", "region": "Central"},
    "Hải Phòng": {"type": "city", "region": "North"},
    "Cần Thơ": {"type": "city", "region": "South"},
    
    # Northern provinces
    "Hà Giang": {"type": "province", "region": "North"},
    "Cao Bằng": {"type": "province", "region": "North"},
    "Bắc Kạn": {"type": "province", "region": "North"},
    "Tuyên Quang": {"type": "province", "region": "North"},
    "Lào Cai": {"type": "province", "region": "North"},
    "Điện Biên": {"type": "province", "region": "North"},
    "Lai Châu": {"type": "province", "region": "North"},
    "Sơn La": {"type": "province", "region": "North"},
    "Yên Bái": {"type": "province", "region": "North"},
    "Hòa Bình": {"type": "province", "region": "North"},
    "Thái Nguyên": {"type": "province", "region": "North"},
    "Lạng Sơn": {"type": "province", "region": "North"},
    "Quảng Ninh": {"type": "province", "region": "North"},
    "Bắc Giang": {"type": "province", "region": "North"},
    "Phú Thọ": {"type": "province", "region": "North"},
    "Vĩnh Phúc": {"type": "province", "region": "North"},
    "Bắc Ninh": {"type": "province", "region": "North"},
    "Hải Dương": {"type": "province", "region": "North"},
    "Hưng Yên": {"type": "province", "region": "North"},
    "Thái Bình": {"type": "province", "region": "North"},
    "Hà Nam": {"type": "province", "region": "North"},
    "Nam Định": {"type": "province", "region": "North"},
    "Ninh Bình": {"type": "province", "region": "North"},
    
    # Central provinces
    "Thanh Hóa": {"type": "province", "region": "Central"},
    "Nghệ An": {"type": "province", "region": "Central"},
    "Hà Tĩnh": {"type": "province", "region": "Central"},
    "Quảng Bình": {"type": "province", "region": "Central"},
    "Quảng Trị": {"type": "province", "region": "Central"},
    "Thừa Thiên Huế": {"type": "province", "region": "Central"},
    "Thừa Thiên – Huế": {"type": "province", "region": "Central"},
    "Quảng Nam": {"type": "province", "region": "Central"},
    "Quảng Ngãi": {"type": "province", "region": "Central"},
    "Bình Định": {"type": "province", "region": "Central"},
    "Phú Yên": {"type": "province", "region": "Central"},
    "Khánh Hòa": {"type": "province", "region": "Central"},
    "Ninh Thuận": {"type": "province", "region": "Central"},
    "Bình Thuận": {"type": "province", "region": "Central"},
    "Kon Tum": {"type": "province", "region": "Central Highlands"},
    "Gia Lai": {"type": "province", "region": "Central Highlands"},
    "Đắk Lắk": {"type": "province", "region": "Central Highlands"},
    "Đắk Nông": {"type": "province", "region": "Central Highlands"},
    "Lâm Đồng": {"type": "province", "region": "Central Highlands"},
    
    # Southern provinces
    "Bình Phước": {"type": "province", "region": "South"},
    "Tây Ninh": {"type": "province", "region": "South"},
    "Bình Dương": {"type": "province", "region": "South"},
    "Đồng Nai": {"type": "province", "region": "South"},
    "Bà Rịa – Vũng Tàu": {"type": "province", "region": "South"},
    "Bà Rịa - Vũng Tàu": {"type": "province", "region": "South"},
    "Long An": {"type": "province", "region": "South"},
    "Tiền Giang": {"type": "province", "region": "South"},
    "Bến Tre": {"type": "province", "region": "South"},
    "Trà Vinh": {"type": "province", "region": "South"},
    "Vĩnh Long": {"type": "province", "region": "South"},
    "Đồng Tháp": {"type": "province", "region": "South"},
    "An Giang": {"type": "province", "region": "South"},
    "Kiên Giang": {"type": "province", "region": "South"},
    "Hậu Giang": {"type": "province", "region": "South"},
    "Sóc Trăng": {"type": "province", "region": "South"},
    "Bạc Liêu": {"type": "province", "region": "South"},
    "Cà Mau": {"type": "province", "region": "South"},
}


class DataQualityImprover:
    """
    Improves data quality for the knowledge graph.
    """
    
    def __init__(self):
        """Initialize the data quality improver."""
        self.provinces_found: Set[str] = set()
        self.stats = {
            "names_fixed": 0,
            "provinces_extracted": 0,
            "birth_years_added": 0,
            "clubs_standardized": 0,
        }
    
    def fix_concatenated_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fix names where foreign and Vietnamese names are concatenated.
        
        Examples:
        - "Maxwell EyerakpoĐinh Hoàng Max" -> "Maxwell Eyerakpo (Đinh Hoàng Max)"
        - "RafaelsonNguyễn Xuân Son" -> "Rafaelson (Nguyễn Xuân Son)"
        
        Args:
            df: DataFrame with 'name' column
            
        Returns:
            DataFrame with fixed names
        """
        if "name" not in df.columns:
            return df
        
        # Pattern: Latin text followed by Vietnamese text (with diacritics)
        # Vietnamese characters with diacritics
        vn_pattern = r'([A-Za-z\s]+)([ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆĐÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ\s]+)'
        
        def fix_name(name):
            if not isinstance(name, str):
                return name
            
            # Check for concatenated pattern
            match = re.match(vn_pattern, name)
            if match:
                foreign_part = match.group(1).strip()
                vn_part = match.group(2).strip()
                
                # Only fix if both parts are substantial
                if len(foreign_part) > 2 and len(vn_part) > 2:
                    self.stats["names_fixed"] += 1
                    return f"{foreign_part} ({vn_part})"
            
            return name
        
        df["name"] = df["name"].apply(fix_name)
        df["canonical_name"] = df["name"]  # Update canonical name too
        
        return df
    
    def extract_province(self, place_of_birth: str) -> Optional[str]:
        """
        Extract Vietnamese province/city from place of birth string.
        
        Args:
            place_of_birth: Place of birth string
            
        Returns:
            Province/city name or None
        """
        if not place_of_birth or not isinstance(place_of_birth, str):
            return None
        
        # Clean the string
        pob = place_of_birth.strip()
        
        # Try to match against known provinces
        for province in VIETNAM_PROVINCES.keys():
            if province.lower() in pob.lower():
                return province
        
        # Try to extract from comma-separated parts
        parts = [p.strip() for p in pob.split(",")]
        for part in parts:
            for province in VIETNAM_PROVINCES.keys():
                if province.lower() == part.lower():
                    return province
        
        # Try district extraction (e.g., "Hưng Nguyên, Nghệ An")
        if len(parts) >= 2:
            for part in parts:
                for province in VIETNAM_PROVINCES.keys():
                    if province.lower() in part.lower():
                        return province
        
        return None
    
    def add_province_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add province column extracted from place_of_birth.
        
        Args:
            df: DataFrame with 'place_of_birth' column
            
        Returns:
            DataFrame with 'province' column
        """
        if "place_of_birth" not in df.columns:
            df["province"] = None
            return df
        
        def extract_prov(pob):
            province = self.extract_province(pob)
            if province:
                self.provinces_found.add(province)
                self.stats["provinces_extracted"] += 1
            return province
        
        df["province"] = df["place_of_birth"].apply(extract_prov)
        
        return df
    
    def add_birth_year(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract birth year from date_of_birth column.
        
        Args:
            df: DataFrame with 'date_of_birth' column
            
        Returns:
            DataFrame with 'birth_year' column
        """
        if "date_of_birth" not in df.columns:
            df["birth_year"] = None
            return df
        
        def extract_year(dob):
            if not dob or not isinstance(dob, str):
                return None
            
            # Try to extract 4-digit year
            match = re.search(r'(\d{4})', str(dob))
            if match:
                year = int(match.group(1))
                # Validate year range (1900-2010 for players)
                if 1900 <= year <= 2010:
                    self.stats["birth_years_added"] += 1
                    return year
            
            return None
        
        df["birth_year"] = df["date_of_birth"].apply(extract_year)
        
        return df
    
    def standardize_club_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize club names by removing common prefixes.
        
        Args:
            df: DataFrame with 'name' column (clubs)
            
        Returns:
            DataFrame with standardized names
        """
        if "name" not in df.columns:
            return df
        
        prefixes_to_remove = [
            "Câu lạc bộ bóng đá ",
            "Câu lạc bộ ",
            "CLB bóng đá ",
            "CLB ",
            "FC ",
        ]
        
        def standardize(name):
            if not isinstance(name, str):
                return name
            
            original = name
            for prefix in prefixes_to_remove:
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break
            
            if name != original:
                self.stats["clubs_standardized"] += 1
            
            return name.strip()
        
        df["short_name"] = df["name"].apply(standardize)
        
        return df
    
    def create_provinces_reference(self) -> pd.DataFrame:
        """
        Create reference table for Vietnamese provinces.
        
        Returns:
            DataFrame with province information
        """
        records = []
        province_id = 1
        
        # First add provinces found in data
        for province in sorted(self.provinces_found):
            info = VIETNAM_PROVINCES.get(province, {"type": "unknown", "region": "Unknown"})
            records.append({
                "province_id": province_id,
                "name": province,
                "type": info["type"],
                "region": info["region"],
            })
            province_id += 1
        
        # Add remaining provinces from the master list
        for province, info in VIETNAM_PROVINCES.items():
            if province not in self.provinces_found:
                records.append({
                    "province_id": province_id,
                    "name": province,
                    "type": info["type"],
                    "region": info["region"],
                })
                province_id += 1
        
        df = pd.DataFrame(records)
        
        # Save
        output_path = PROCESSED_DATA_DIR / "provinces_reference.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} provinces to {output_path}")
        
        return df
    
    def build_born_in_edges(self, players_df: pd.DataFrame) -> pd.DataFrame:
        """
        Build BORN_IN edges connecting players to provinces.
        
        Args:
            players_df: DataFrame with 'wiki_id' and 'province' columns
            
        Returns:
            DataFrame with edges
        """
        if "province" not in players_df.columns:
            return pd.DataFrame(columns=["player_wiki_id", "province_name"])
        
        edges = []
        for _, row in players_df.iterrows():
            if pd.notna(row.get("province")):
                edges.append({
                    "player_wiki_id": row["wiki_id"],
                    "province_name": row["province"],
                })
        
        df = pd.DataFrame(edges)
        
        # Save
        output_path = EDGES_DATA_DIR / "born_in.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} born_in edges to {output_path}")
        
        return df
    
    def improve_players(self) -> pd.DataFrame:
        """
        Apply all improvements to player data.
        
        Returns:
            Improved DataFrame
        """
        # Load current data
        input_path = PROCESSED_DATA_DIR / "players_clean.csv"
        if not input_path.exists():
            logger.error(f"File not found: {input_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(input_path)
        original_count = len(df)
        logger.info(f"Loaded {original_count} players from {input_path}")
        
        # Apply improvements
        logger.info("Fixing concatenated names...")
        df = self.fix_concatenated_names(df)
        
        logger.info("Extracting provinces from place_of_birth...")
        df = self.add_province_column(df)
        
        logger.info("Adding birth_year column...")
        df = self.add_birth_year(df)
        
        # Save improved data
        df.to_csv(input_path, index=False, encoding="utf-8")
        logger.info(f"Saved improved players to {input_path}")
        
        return df
    
    def improve_clubs(self) -> pd.DataFrame:
        """
        Apply improvements to club data.
        
        Returns:
            Improved DataFrame
        """
        input_path = PROCESSED_DATA_DIR / "clubs_clean.csv"
        if not input_path.exists():
            logger.error(f"File not found: {input_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(input_path)
        logger.info(f"Loaded {len(df)} clubs from {input_path}")
        
        # Apply improvements
        logger.info("Standardizing club names...")
        df = self.standardize_club_names(df)
        
        # Save improved data
        df.to_csv(input_path, index=False, encoding="utf-8")
        logger.info(f"Saved improved clubs to {input_path}")
        
        return df
    
    def improve_all(self) -> Dict[str, pd.DataFrame]:
        """
        Apply all improvements to all entity types.
        
        Returns:
            Dictionary of improved DataFrames
        """
        results = {}
        
        # Improve players
        logger.info("\n" + "=" * 60)
        logger.info("IMPROVING PLAYERS")
        logger.info("=" * 60)
        players_df = self.improve_players()
        results["player"] = players_df
        
        # Improve clubs
        logger.info("\n" + "=" * 60)
        logger.info("IMPROVING CLUBS")
        logger.info("=" * 60)
        clubs_df = self.improve_clubs()
        results["club"] = clubs_df
        
        # Create provinces reference
        logger.info("\n" + "=" * 60)
        logger.info("CREATING PROVINCE REFERENCE")
        logger.info("=" * 60)
        provinces_df = self.create_provinces_reference()
        results["province"] = provinces_df
        
        # Build born_in edges
        logger.info("\n" + "=" * 60)
        logger.info("BUILDING BORN_IN EDGES")
        logger.info("=" * 60)
        born_in_df = self.build_born_in_edges(players_df)
        results["born_in"] = born_in_df
        
        # Print summary
        self._print_summary()
        
        return results
    
    def _print_summary(self) -> None:
        """Print improvement summary."""
        print("\n" + "=" * 60)
        print("DATA QUALITY IMPROVEMENT SUMMARY")
        print("=" * 60)
        print(f"  Names fixed (concatenation): {self.stats['names_fixed']}")
        print(f"  Provinces extracted: {self.stats['provinces_extracted']}")
        print(f"  Birth years added: {self.stats['birth_years_added']}")
        print(f"  Club names standardized: {self.stats['clubs_standardized']}")
        print(f"  Unique provinces found: {len(self.provinces_found)}")
        print("=" * 60)


def main():
    """Main entry point for data quality CLI."""
    parser = argparse.ArgumentParser(
        description="Improve data quality for the knowledge graph",
    )
    
    parser.add_argument(
        "--improve-all",
        action="store_true",
        help="Apply all improvements",
    )
    parser.add_argument(
        "--fix-names",
        action="store_true",
        help="Fix concatenated names only",
    )
    parser.add_argument(
        "--extract-provinces",
        action="store_true",
        help="Extract provinces only",
    )
    
    args = parser.parse_args()
    
    if not any([args.improve_all, args.fix_names, args.extract_provinces]):
        parser.error("Must specify an action (--improve-all, --fix-names, etc.)")
    
    improver = DataQualityImprover()
    
    if args.improve_all:
        improver.improve_all()
    elif args.fix_names:
        improver.improve_players()
    elif args.extract_provinces:
        df = pd.read_csv(PROCESSED_DATA_DIR / "players_clean.csv")
        df = improver.add_province_column(df)
        improver.create_provinces_reference()
        improver.build_born_in_edges(df)


if __name__ == "__main__":
    main()
