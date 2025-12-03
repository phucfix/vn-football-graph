"""
Player Data Cleaner for Vietnamese Football Knowledge Graph

This module filters and cleans player data to include only Vietnamese players,
then expands the data with additional computed fields.

Features:
- Filter only Vietnamese players based on:
  - place_of_birth containing Vietnamese locations
  - national_team_history containing Vietnamese national teams
  - clubs_history containing Vietnamese clubs
- Normalize and standardize data
- Expand with computed fields like:
  - birth_year
  - province (extracted from place_of_birth)
  - total_appearances, total_goals
  - career_start_year, career_end_year
  - is_national_team_player

Usage:
    python -m processor.player_cleaner
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    PROCESSED_DATA_DIR,
    get_parsed_file_path,
    get_processed_file_path,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# VIETNAMESE LOCATION PATTERNS
# =============================================================================

# Vietnamese provinces and cities
VIETNAMESE_PROVINCES = {
    # Miền Bắc (Northern Vietnam)
    "Hà Nội", "Hải Phòng", "Hải Dương", "Hưng Yên", "Thái Bình", "Nam Định",
    "Ninh Bình", "Hà Nam", "Vĩnh Phúc", "Phú Thọ", "Thái Nguyên", "Bắc Giang",
    "Bắc Ninh", "Quảng Ninh", "Lạng Sơn", "Cao Bằng", "Hà Giang", "Tuyên Quang",
    "Lào Cai", "Yên Bái", "Sơn La", "Điện Biên", "Lai Châu", "Hòa Bình",
    "Bắc Kạn",
    
    # Miền Trung (Central Vietnam)
    "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Bình", "Quảng Trị", "Thừa Thiên Huế",
    "Đà Nẵng", "Quảng Nam", "Quảng Ngãi", "Bình Định", "Phú Yên", "Khánh Hòa",
    "Ninh Thuận", "Bình Thuận",
    
    # Tây Nguyên (Central Highlands)
    "Kon Tum", "Gia Lai", "Đắk Lắk", "Đắk Nông", "Lâm Đồng",
    
    # Miền Nam (Southern Vietnam)
    "Thành phố Hồ Chí Minh", "Hồ Chí Minh", "Sài Gòn", "TP.HCM", "TP HCM",
    "Bình Dương", "Đồng Nai", "Bà Rịa-Vũng Tàu", "Bà Rịa Vũng Tàu", "Vũng Tàu",
    "Tây Ninh", "Bình Phước", "Long An", "Tiền Giang", "Bến Tre", "Vĩnh Long",
    "Trà Vinh", "Đồng Tháp", "An Giang", "Kiên Giang", "Cần Thơ", "Hậu Giang",
    "Sóc Trăng", "Bạc Liêu", "Cà Mau",
}

# Historical Vietnamese locations
HISTORICAL_VIETNAM_PATTERNS = [
    "Việt Nam", "Vietnam", "VN",
    "Việt Nam Cộng hòa", "Việt Nam Cộng Hòa", "VNCH",
    "Việt Nam Dân chủ Cộng hòa", "VNDCCH",
    "Liên bang Đông Dương", "Đông Dương",
    "Nam Kỳ", "Bắc Kỳ", "Trung Kỳ",
]

# Vietnamese national team patterns
VIETNAMESE_NATIONAL_TEAMS = [
    "Việt Nam",
    "U-23 Việt Nam", "U23 Việt Nam",
    "U-22 Việt Nam", "U22 Việt Nam",
    "U-21 Việt Nam", "U21 Việt Nam",
    "U-20 Việt Nam", "U20 Việt Nam",
    "U-19 Việt Nam", "U19 Việt Nam",
    "U-18 Việt Nam", "U18 Việt Nam",
    "U-17 Việt Nam", "U17 Việt Nam",
    "U-16 Việt Nam", "U16 Việt Nam",
    "U-15 Việt Nam", "U15 Việt Nam",
    "U-14 Việt Nam", "U14 Việt Nam",
    "Olympic Việt Nam",
    "Việt Nam Dân chủ Cộng hòa",
    "Việt Nam Cộng hòa", "Việt Nam Cộng Hòa",
    "Đội tuyển Việt Nam", "ĐTQG Việt Nam",
    "nft|Việt Nam", "nftu|Việt Nam",
]

# Vietnamese clubs
VIETNAMESE_CLUBS = [
    "Hà Nội", "Hà Nội T&T", "Hà Nội ACB", "T&T Hà Nội",
    "Sông Lam Nghệ An", "SLNA",
    "Becamex Bình Dương", "Bình Dương",
    "Hoàng Anh Gia Lai", "HAGL",
    "Viettel", "Thể Công", "Thể Công-Viettel",
    "Hải Phòng", "Vicem Hải Phòng",
    "SHB Đà Nẵng", "Đà Nẵng",
    "Thanh Hóa", "FLC Thanh Hóa", "Đông Á Thanh Hóa",
    "Nam Định", "Thép Xanh Nam Định",
    "Than Quảng Ninh", "Quảng Ninh",
    "Sài Gòn", "Sài Gòn FC",
    "Long An", "Đồng Tâm Long An",
    "Đồng Tháp", "TĐCS Đồng Tháp",
    "Bình Định", "Topenland Bình Định", "Quy Nhơn Bình Định",
    "Khánh Hòa", "Sanna Khánh Hòa",
    "Quảng Nam", "QNK Quảng Nam",
    "Cần Thơ", "XSKT Cần Thơ",
    "Ninh Bình", "The Vissai Ninh Bình", "Xi măng The Vissai Ninh Bình",
    "Hồng Lĩnh Hà Tĩnh", "Hà Tĩnh",
    "Thành phố Hồ Chí Minh", "TP.HCM", "HCMC",
    "Công an Hà Nội", "Công An Hà Nội",
    "Công an Thành phố Hồ Chí Minh", "Cảng Sài Gòn",
    "PVF-CAND", "PVF–CAND",
    "Đồng Nai", "Trường Tươi Đồng Nai",
]


class PlayerCleaner:
    """
    Cleaner for Vietnamese football players data.
    """
    
    def __init__(self):
        """Initialize the player cleaner."""
        self.stats = {
            "total_players": 0,
            "vietnamese_players": 0,
            "filtered_out": 0,
            "by_place_of_birth": 0,
            "by_national_team": 0,
            "by_clubs": 0,
        }
    
    def load_players(self) -> pd.DataFrame:
        """
        Load players from JSONL file.
        
        Returns:
            DataFrame with player data
        """
        file_path = get_parsed_file_path("player")
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
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
        
        self.stats["total_players"] = len(records)
        logger.info(f"Loaded {len(records)} players from {file_path}")
        return pd.DataFrame(records)
    
    def is_vietnamese_place(self, place: Optional[str]) -> bool:
        """
        Check if a place_of_birth is in Vietnam.
        
        Args:
            place: Place of birth string
            
        Returns:
            True if the place is in Vietnam
        """
        if not place or pd.isna(place):
            return False
        
        place_str = str(place).lower()
        
        # Check for Vietnamese provinces
        for province in VIETNAMESE_PROVINCES:
            if province.lower() in place_str:
                return True
        
        # Check for historical Vietnam patterns
        for pattern in HISTORICAL_VIETNAM_PATTERNS:
            if pattern.lower() in place_str:
                return True
        
        return False
    
    def is_vietnamese_national_team_player(self, national_team_history: any) -> bool:
        """
        Check if player has played for Vietnamese national team.
        
        Args:
            national_team_history: National team history (list or JSON string)
            
        Returns:
            True if player has Vietnamese national team history
        """
        if not national_team_history:
            return False
        
        # Parse if string
        if isinstance(national_team_history, str):
            try:
                national_team_history = json.loads(national_team_history)
            except:
                # Check string directly
                for team in VIETNAMESE_NATIONAL_TEAMS:
                    if team.lower() in national_team_history.lower():
                        return True
                return False
        
        if not isinstance(national_team_history, list):
            return False
        
        for entry in national_team_history:
            if isinstance(entry, dict):
                team_name = entry.get("club_name", "")
            else:
                team_name = str(entry)
            
            if not team_name:
                continue
            
            team_lower = team_name.lower()
            for vn_team in VIETNAMESE_NATIONAL_TEAMS:
                if vn_team.lower() in team_lower:
                    return True
        
        return False
    
    def has_vietnamese_club_history(self, clubs_history: any) -> bool:
        """
        Check if player has played for Vietnamese clubs.
        
        Args:
            clubs_history: Clubs history (list or JSON string)
            
        Returns:
            True if player has Vietnamese club history
        """
        if not clubs_history:
            return False
        
        # Parse if string
        if isinstance(clubs_history, str):
            try:
                clubs_history = json.loads(clubs_history)
            except:
                # Check string directly
                for club in VIETNAMESE_CLUBS:
                    if club.lower() in clubs_history.lower():
                        return True
                return False
        
        if not isinstance(clubs_history, list):
            return False
        
        for entry in clubs_history:
            if isinstance(entry, dict):
                club_name = entry.get("club_name", "")
            else:
                club_name = str(entry)
            
            if not club_name:
                continue
            
            club_lower = club_name.lower()
            for vn_club in VIETNAMESE_CLUBS:
                if vn_club.lower() in club_lower:
                    return True
        
        return False
    
    def filter_vietnamese_players(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to keep only Vietnamese players.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Filtered DataFrame with only Vietnamese players
        """
        if df.empty:
            return df
        
        def is_vietnamese(row):
            # Check place of birth
            if self.is_vietnamese_place(row.get("place_of_birth")):
                return "place_of_birth"
            
            # Check national team history
            if self.is_vietnamese_national_team_player(row.get("national_team_history")):
                return "national_team"
            
            # Check clubs history
            if self.has_vietnamese_club_history(row.get("clubs_history")):
                return "clubs"
            
            return None
        
        # Apply filter
        df["_vn_reason"] = df.apply(is_vietnamese, axis=1)
        
        # Count reasons
        self.stats["by_place_of_birth"] = (df["_vn_reason"] == "place_of_birth").sum()
        self.stats["by_national_team"] = (df["_vn_reason"] == "national_team").sum()
        self.stats["by_clubs"] = (df["_vn_reason"] == "clubs").sum()
        
        # Filter
        df_filtered = df[df["_vn_reason"].notna()].copy()
        df_filtered = df_filtered.drop(columns=["_vn_reason"])
        
        self.stats["vietnamese_players"] = len(df_filtered)
        self.stats["filtered_out"] = len(df) - len(df_filtered)
        
        logger.info(f"Filtered to {len(df_filtered)} Vietnamese players")
        logger.info(f"  - By place of birth: {self.stats['by_place_of_birth']}")
        logger.info(f"  - By national team: {self.stats['by_national_team']}")
        logger.info(f"  - By clubs: {self.stats['by_clubs']}")
        logger.info(f"  - Filtered out: {self.stats['filtered_out']}")
        
        return df_filtered
    
    def extract_province(self, place: Optional[str]) -> Optional[str]:
        """
        Extract province from place_of_birth.
        
        Args:
            place: Place of birth string
            
        Returns:
            Province name or None
        """
        if not place or pd.isna(place):
            return None
        
        place_str = str(place)
        
        # Try to match Vietnamese provinces
        for province in VIETNAMESE_PROVINCES:
            if province in place_str:
                return province
        
        # Special cases
        if "Sài Gòn" in place_str:
            return "Thành phố Hồ Chí Minh"
        if "TP.HCM" in place_str or "TP HCM" in place_str:
            return "Thành phố Hồ Chí Minh"
        
        return None
    
    def extract_birth_year(self, dob: Optional[str]) -> Optional[int]:
        """
        Extract birth year from date_of_birth.
        
        Args:
            dob: Date of birth string
            
        Returns:
            Birth year or None
        """
        if not dob or pd.isna(dob):
            return None
        
        dob_str = str(dob)
        
        # Try to find 4-digit year
        year_match = re.search(r"(\d{4})", dob_str)
        if year_match:
            year = int(year_match.group(1))
            if 1940 <= year <= 2010:  # Reasonable range for football players
                return year
        
        return None
    
    def calculate_career_stats(self, history: any) -> Dict:
        """
        Calculate career statistics from history.
        
        Args:
            history: Career history (list or JSON string)
            
        Returns:
            Dict with total_appearances, total_goals, start_year, end_year
        """
        result = {
            "total_appearances": 0,
            "total_goals": 0,
            "career_start_year": None,
            "career_end_year": None,
        }
        
        if not history:
            return result
        
        # Parse if string
        if isinstance(history, str):
            try:
                history = json.loads(history)
            except:
                return result
        
        if not isinstance(history, list):
            return result
        
        years = []
        
        for entry in history:
            if not isinstance(entry, dict):
                continue
            
            # Appearances and goals - with validation for reasonable values
            appearances = entry.get("appearances")
            if appearances and isinstance(appearances, (int, float)):
                app_val = int(appearances)
                # Validate: max reasonable appearances per club is ~1000
                if 0 <= app_val <= 2000:
                    result["total_appearances"] += app_val
            
            goals = entry.get("goals")
            if goals and isinstance(goals, (int, float)):
                goal_val = int(goals)
                # Validate: max reasonable goals per club is ~1000
                if 0 <= goal_val <= 2000:
                    result["total_goals"] += goal_val
            
            # Years
            from_year = entry.get("from_year")
            to_year = entry.get("to_year")
            
            if from_year and isinstance(from_year, (int, float)):
                years.append(int(from_year))
            if to_year and isinstance(to_year, (int, float)):
                years.append(int(to_year))
        
        if years:
            result["career_start_year"] = min(years)
            result["career_end_year"] = max(years)
        
        return result
    
    def normalize_height(self, height: Optional[str]) -> Optional[float]:
        """
        Normalize height to meters.
        
        Args:
            height: Height string (e.g., "1,78 m", "178 cm")
            
        Returns:
            Height in meters or None
        """
        if not height or pd.isna(height):
            return None
        
        height_str = str(height).strip().lower()
        
        # Remove non-numeric characters except comma, dot
        height_str = re.sub(r"[^\d,.]", " ", height_str).strip()
        
        if not height_str:
            return None
        
        # Try to parse
        try:
            # Replace comma with dot
            height_str = height_str.replace(",", ".")
            
            # Split on spaces and take first number
            parts = height_str.split()
            if parts:
                value = float(parts[0])
                
                # If value > 100, assume it's in cm
                if value > 100:
                    return round(value / 100, 2)
                elif value > 2.5:  # If > 2.5, might be cm without proper parsing
                    return round(value / 100, 2)
                else:
                    return round(value, 2)
        except:
            pass
        
        return None
    
    def normalize_position(self, position: Optional[str]) -> Optional[str]:
        """
        Normalize position to standard codes.
        
        Args:
            position: Position string
            
        Returns:
            Normalized position code
        """
        if not position or pd.isna(position):
            return None
        
        pos_str = str(position).strip().upper()
        
        # Position mappings
        position_map = {
            # Goalkeeper
            "GK": "GK", "TM": "GK", "THỦ MÔN": "GK",
            
            # Defenders
            "DF": "DF", "CB": "CB", "LB": "LB", "RB": "RB",
            "FB": "FB", "SW": "SW", "WB": "WB",
            "LWB": "LWB", "RWB": "RWB",
            
            # Midfielders
            "MF": "MF", "CM": "CM", "DM": "DM", "AM": "AM",
            "LM": "LM", "RM": "RM", "WM": "WM",
            "CDM": "DM", "CAM": "AM",
            
            # Forwards
            "FW": "FW", "ST": "ST", "CF": "CF",
            "LW": "LW", "RW": "RW", "WF": "WF",
            "SS": "SS",
        }
        
        # Try direct match
        if pos_str in position_map:
            return position_map[pos_str]
        
        # Try partial match
        for key, value in position_map.items():
            if key in pos_str:
                return value
        
        return pos_str[:3] if len(pos_str) >= 3 else pos_str
    
    def expand_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Expand player data with computed fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with expanded fields
        """
        if df.empty:
            return df
        
        logger.info("Expanding player data with computed fields...")
        
        # Extract province from place_of_birth
        df["province"] = df["place_of_birth"].apply(self.extract_province)
        
        # Extract birth year
        df["birth_year"] = df["date_of_birth"].apply(self.extract_birth_year)
        
        # Normalize height
        df["height_m"] = df["height"].apply(self.normalize_height)
        
        # Normalize position
        df["position_normalized"] = df["position"].apply(self.normalize_position)
        
        # Calculate club career stats
        club_stats = df["clubs_history"].apply(self.calculate_career_stats)
        df["club_appearances"] = club_stats.apply(lambda x: x.get("total_appearances", 0))
        df["club_goals"] = club_stats.apply(lambda x: x.get("total_goals", 0))
        df["career_start_year"] = club_stats.apply(lambda x: x.get("career_start_year"))
        df["career_end_year"] = club_stats.apply(lambda x: x.get("career_end_year"))
        
        # Calculate national team stats
        nt_stats = df["national_team_history"].apply(self.calculate_career_stats)
        df["national_team_appearances"] = nt_stats.apply(lambda x: x.get("total_appearances", 0))
        df["national_team_goals"] = nt_stats.apply(lambda x: x.get("total_goals", 0))
        
        # Is national team player
        df["is_national_team_player"] = df["national_team_history"].apply(
            self.is_vietnamese_national_team_player
        )
        
        # Nationality normalized (always Vietnam for filtered data)
        df["nationality_normalized"] = "Vietnam"
        
        # Years active
        def calc_years_active(row):
            start = row.get("career_start_year")
            end = row.get("career_end_year")
            if start and end:
                return end - start + 1
            return None
        
        df["years_active"] = df.apply(calc_years_active, axis=1)
        
        return df
    
    def deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate players, keeping the one with more information.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Deduplicated DataFrame
        """
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Calculate information completeness score for each row
        def calc_info_score(row):
            score = 0
            # Has national team history
            nt_history = row.get("national_team_history")
            if nt_history:
                if isinstance(nt_history, str):
                    try:
                        nt_list = json.loads(nt_history)
                        score += len(nt_list) * 10
                    except:
                        pass
                elif isinstance(nt_history, list):
                    score += len(nt_history) * 10
            
            # Has club history
            clubs = row.get("clubs_history")
            if clubs:
                if isinstance(clubs, str):
                    try:
                        clubs_list = json.loads(clubs)
                        score += len(clubs_list) * 5
                    except:
                        pass
                elif isinstance(clubs, list):
                    score += len(clubs) * 5
            
            # Has place of birth
            if row.get("place_of_birth") and not pd.isna(row.get("place_of_birth")):
                score += 3
            
            # Has date of birth
            if row.get("date_of_birth") and not pd.isna(row.get("date_of_birth")):
                score += 3
            
            # Has height
            if row.get("height") and not pd.isna(row.get("height")):
                score += 2
            
            # Has current club
            if row.get("current_club") and not pd.isna(row.get("current_club")):
                score += 1
            
            return score
        
        df["_info_score"] = df.apply(calc_info_score, axis=1)
        
        # Sort by info score (descending) then by wiki_id (ascending, prefer older)
        df = df.sort_values(["_info_score", "wiki_id"], ascending=[False, True])
        
        # Deduplicate by name, keeping first (highest score)
        df = df.drop_duplicates(subset=["name"], keep="first")
        
        # Remove helper column
        df = df.drop(columns=["_info_score"])
        
        removed = original_count - len(df)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate players")
        
        return df
    
    def create_canonical_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create canonical names for players with duplicate names.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with canonical_name column
        """
        if df.empty or "name" not in df.columns:
            return df
        
        # Count name occurrences
        name_counts = df["name"].value_counts()
        duplicate_names = set(name_counts[name_counts > 1].index)
        
        def make_canonical(row):
            name = row.get("name", "")
            if name in duplicate_names:
                # Try to add birth year
                birth_year = row.get("birth_year")
                if birth_year and not pd.isna(birth_year):
                    return f"{name} ({int(birth_year)})"
                # Fallback to wiki_id
                wiki_id = row.get("wiki_id", "")
                if wiki_id:
                    return f"{name} (#{wiki_id})"
            return name
        
        df["canonical_name"] = df.apply(make_canonical, axis=1)
        
        return df
    
    def flatten_history_to_json(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure history columns are JSON strings.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with JSON-stringified history columns
        """
        history_columns = ["clubs_history", "national_team_history"]
        
        def to_json_str(val):
            if val is None:
                return "[]"
            try:
                if pd.isna(val):
                    return "[]"
            except (ValueError, TypeError):
                pass
            if isinstance(val, list):
                return json.dumps(val, ensure_ascii=False)
            if isinstance(val, str):
                return val
            return "[]"
        
        for col in history_columns:
            if col in df.columns:
                df[col] = df[col].apply(to_json_str)
        
        return df
    
    def process(self) -> pd.DataFrame:
        """
        Main processing pipeline.
        
        Returns:
            Cleaned and expanded DataFrame
        """
        # Load data
        df = self.load_players()
        
        if df.empty:
            logger.error("No players loaded")
            return df
        
        # Filter Vietnamese players
        df = self.filter_vietnamese_players(df)
        
        if df.empty:
            logger.error("No Vietnamese players found")
            return df
        
        # Deduplicate
        df = self.deduplicate(df)
        
        # Expand data
        df = self.expand_data(df)
        
        # Create canonical names
        df = self.create_canonical_names(df)
        
        # Flatten history to JSON
        df = self.flatten_history_to_json(df)
        
        # Select and order output columns
        output_columns = [
            "wiki_id", "name", "canonical_name", "full_name",
            "date_of_birth", "birth_year", "place_of_birth", "province",
            "nationality_normalized",
            "position", "position_normalized",
            "height", "height_m",
            "current_club",
            "clubs_history", "national_team_history",
            "club_appearances", "club_goals",
            "national_team_appearances", "national_team_goals",
            "is_national_team_player",
            "career_start_year", "career_end_year", "years_active",
            "wiki_url", "wiki_title",
        ]
        
        # Only include columns that exist
        output_columns = [c for c in output_columns if c in df.columns]
        df = df[output_columns]
        
        return df
    
    def save(self, df: pd.DataFrame, output_path: Optional[Path] = None) -> Path:
        """
        Save processed data to CSV.
        
        Args:
            df: DataFrame to save
            output_path: Optional output path
            
        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = PROCESSED_DATA_DIR / "players_vn_clean.csv"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} Vietnamese players to {output_path}")
        
        return output_path
    
    def print_stats(self):
        """Print processing statistics."""
        print("\n" + "=" * 60)
        print("PLAYER CLEANING STATISTICS")
        print("=" * 60)
        print(f"Total players loaded:      {self.stats['total_players']}")
        print(f"Vietnamese players:        {self.stats['vietnamese_players']}")
        print(f"  - By place of birth:     {self.stats['by_place_of_birth']}")
        print(f"  - By national team:      {self.stats['by_national_team']}")
        print(f"  - By clubs:              {self.stats['by_clubs']}")
        print(f"Filtered out:              {self.stats['filtered_out']}")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean and filter Vietnamese football players data"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path",
    )
    parser.add_argument(
        "--update-main",
        action="store_true",
        help="Also update the main players_clean.csv file",
    )
    
    args = parser.parse_args()
    
    # Process
    cleaner = PlayerCleaner()
    df = cleaner.process()
    
    if df.empty:
        logger.error("No data to save")
        return 1
    
    # Save
    output_path = Path(args.output) if args.output else None
    saved_path = cleaner.save(df, output_path)
    
    # Update main file if requested
    if args.update_main:
        main_path = PROCESSED_DATA_DIR / "players_clean.csv"
        cleaner.save(df, main_path)
    
    # Print stats
    cleaner.print_stats()
    
    # Print sample
    print("\nSample output (first 5 rows):")
    print(df[["name", "province", "position_normalized", "is_national_team_player"]].head(10))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
