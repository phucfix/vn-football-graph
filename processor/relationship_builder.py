"""
Relationship Builder for Vietnamese Football Knowledge Graph

This module builds edge tables (relationships) from cleaned entity CSVs.

Relationships generated:
- LAYER 1 (direct from infobox):
  - played_for: player -> club
  - played_for_national: player -> national_team
  - coached: coach -> club
  - coached_national: coach -> national_team

- LAYER 2 (derived):
  - teammate: player <-> player (same club, overlapping time)
  - under_coach: player -> coach (same club, overlapping time)
  - national_teammate: player <-> player (same national team)

- LAYER 3 (semantic):
  - has_position: player -> position
  - has_nationality: player/coach -> nationality

Usage:
    python -m processor.relationship_builder --build-all
    python -m processor.relationship_builder --build played_for
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    EDGES_DATA_DIR,
    PROCESSED_DATA_DIR,
    get_edge_file_path,
    get_processed_file_path,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RelationshipBuilder:
    """
    Builder for generating relationship/edge tables.
    """
    
    def __init__(self):
        """Initialize the relationship builder."""
        self.stats = {}
        
        # Cache for loaded DataFrames
        self._players_df: Optional[pd.DataFrame] = None
        self._coaches_df: Optional[pd.DataFrame] = None
        self._clubs_df: Optional[pd.DataFrame] = None
        self._teams_df: Optional[pd.DataFrame] = None
        self._positions_df: Optional[pd.DataFrame] = None
        self._nationalities_df: Optional[pd.DataFrame] = None
        
        # Lookup tables for name -> wiki_id mapping
        self._club_name_to_id: Dict[str, int] = {}
        self._team_name_to_id: Dict[str, int] = {}
    
    def _load_csv(self, filename: str) -> pd.DataFrame:
        """Load a CSV file from the processed directory."""
        file_path = PROCESSED_DATA_DIR / filename
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return pd.DataFrame()
        return pd.read_csv(file_path, encoding="utf-8")
    
    @property
    def players_df(self) -> pd.DataFrame:
        """Lazy-load players DataFrame."""
        if self._players_df is None:
            self._players_df = self._load_csv("players_clean.csv")
        return self._players_df
    
    @property
    def coaches_df(self) -> pd.DataFrame:
        """Lazy-load coaches DataFrame."""
        if self._coaches_df is None:
            self._coaches_df = self._load_csv("coaches_clean.csv")
        return self._coaches_df
    
    @property
    def clubs_df(self) -> pd.DataFrame:
        """Lazy-load clubs DataFrame."""
        if self._clubs_df is None:
            self._clubs_df = self._load_csv("clubs_clean.csv")
            # Build name lookup
            if not self._clubs_df.empty:
                for _, row in self._clubs_df.iterrows():
                    name = str(row.get("name", "")).lower().strip()
                    canonical = str(row.get("canonical_name", "")).lower().strip()
                    wiki_id = row.get("wiki_id")
                    if name and wiki_id:
                        self._club_name_to_id[name] = wiki_id
                    if canonical and wiki_id:
                        self._club_name_to_id[canonical] = wiki_id
        return self._clubs_df
    
    @property
    def teams_df(self) -> pd.DataFrame:
        """Lazy-load national teams DataFrame."""
        if self._teams_df is None:
            self._teams_df = self._load_csv("national_teams_clean.csv")
            # Build name lookup
            if not self._teams_df.empty:
                for _, row in self._teams_df.iterrows():
                    name = str(row.get("name", "")).lower().strip()
                    canonical = str(row.get("canonical_name", "")).lower().strip()
                    wiki_id = row.get("wiki_id")
                    if name and wiki_id:
                        self._team_name_to_id[name] = wiki_id
                    if canonical and wiki_id:
                        self._team_name_to_id[canonical] = wiki_id
        return self._teams_df
    
    @property
    def positions_df(self) -> pd.DataFrame:
        """Lazy-load positions DataFrame."""
        if self._positions_df is None:
            self._positions_df = self._load_csv("positions_reference.csv")
        return self._positions_df
    
    @property
    def nationalities_df(self) -> pd.DataFrame:
        """Lazy-load nationalities DataFrame."""
        if self._nationalities_df is None:
            self._nationalities_df = self._load_csv("nationalities_reference.csv")
        return self._nationalities_df
    
    @property
    def stadiums_df(self) -> pd.DataFrame:
        """Lazy-load stadiums DataFrame."""
        if not hasattr(self, '_stadiums_df') or self._stadiums_df is None:
            self._stadiums_df = self._load_csv("stadiums_clean.csv")
            # Build name lookup
            if not self._stadiums_df.empty:
                if not hasattr(self, '_stadium_name_to_id'):
                    self._stadium_name_to_id = {}
                for _, row in self._stadiums_df.iterrows():
                    name = str(row.get("name", "")).lower().strip()
                    canonical = str(row.get("canonical_name", "")).lower().strip()
                    wiki_id = row.get("wiki_id")
                    if name and wiki_id:
                        self._stadium_name_to_id[name] = wiki_id
                    if canonical and wiki_id:
                        self._stadium_name_to_id[canonical] = wiki_id
        return self._stadiums_df
    
    @property
    def competitions_df(self) -> pd.DataFrame:
        """Lazy-load competitions DataFrame."""
        if not hasattr(self, '_competitions_df') or self._competitions_df is None:
            self._competitions_df = self._load_csv("competitions_clean.csv")
        return self._competitions_df
    
    def _parse_json_field(self, value: Any) -> List[Dict]:
        """Parse a JSON string field into a list of dicts."""
        if pd.isna(value) or not value:
            return []
        
        if isinstance(value, list):
            return value
        
        try:
            parsed = json.loads(str(value))
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def _match_club_name(self, club_name: str) -> Optional[int]:
        """
        Try to match a club name to a wiki_id.
        
        Args:
            club_name: Club name from career history
            
        Returns:
            wiki_id if found, None otherwise
        """
        if not club_name:
            return None
        
        name_lower = club_name.lower().strip()
        
        # Direct lookup
        if name_lower in self._club_name_to_id:
            return self._club_name_to_id[name_lower]
        
        # Fuzzy match (check if any club name is contained)
        for known_name, wiki_id in self._club_name_to_id.items():
            if known_name in name_lower or name_lower in known_name:
                return wiki_id
        
        return None
    
    def _match_team_name(self, team_name: str) -> Optional[int]:
        """Try to match a national team name to a wiki_id."""
        if not team_name:
            return None
        
        name_lower = team_name.lower().strip()
        
        # Direct lookup
        if name_lower in self._team_name_to_id:
            return self._team_name_to_id[name_lower]
        
        # Check for Vietnam national team variations
        vietnam_keywords = ["việt nam", "vietnam", "u23", "u22", "u21", "u20", "u19"]
        if any(kw in name_lower for kw in vietnam_keywords):
            # Find the most specific match
            for known_name, wiki_id in self._team_name_to_id.items():
                if any(kw in known_name for kw in vietnam_keywords):
                    return wiki_id
        
        return None
    
    def _years_overlap(
        self,
        start1: Optional[int],
        end1: Optional[int],
        start2: Optional[int],
        end2: Optional[int],
    ) -> bool:
        """Check if two year ranges overlap."""
        # Handle None values (ongoing/current = 2025)
        current_year = 2025
        end1 = end1 or current_year
        end2 = end2 or current_year
        start1 = start1 or 1900
        start2 = start2 or 1900
        
        return start1 <= end2 and start2 <= end1
    
    def _get_overlap_range(
        self,
        start1: Optional[int],
        end1: Optional[int],
        start2: Optional[int],
        end2: Optional[int],
    ) -> Tuple[Optional[int], Optional[int]]:
        """Get the overlapping year range."""
        current_year = 2025
        end1 = end1 or current_year
        end2 = end2 or current_year
        start1 = start1 or 1900
        start2 = start2 or 1900
        
        if not self._years_overlap(start1, end1, start2, end2):
            return None, None
        
        return max(start1, start2), min(end1, end2)
    
    def build_played_for(self) -> pd.DataFrame:
        """
        Build PLAYED_FOR relationships (player -> club).
        
        Returns:
            DataFrame with played_for edges
        """
        if self.players_df.empty:
            logger.warning("No player data available")
            return pd.DataFrame()
        
        # Load clubs to build lookup
        _ = self.clubs_df
        
        edges = []
        
        for _, player in tqdm(
            self.players_df.iterrows(),
            desc="Building played_for edges",
            total=len(self.players_df),
        ):
            player_id = player["wiki_id"]
            clubs_history = self._parse_json_field(player.get("clubs_history"))
            
            for stint in clubs_history:
                club_name = stint.get("club_name")
                if not club_name:
                    continue
                
                club_id = self._match_club_name(club_name)
                
                edges.append({
                    "from_player_id": player_id,
                    "to_club_id": club_id,
                    "to_club_name": club_name,  # Keep name for unmatched clubs
                    "from_year": stint.get("from_year"),
                    "to_year": stint.get("to_year"),
                    "appearances": stint.get("appearances"),
                    "goals": stint.get("goals"),
                })
        
        df = pd.DataFrame(edges)
        self.stats["played_for"] = len(df)
        logger.info(f"Built {len(df)} played_for edges")
        
        return df
    
    def build_played_for_national(self) -> pd.DataFrame:
        """
        Build PLAYED_FOR_NATIONAL relationships (player -> national_team).
        
        Returns:
            DataFrame with played_for_national edges
        """
        if self.players_df.empty:
            return pd.DataFrame()
        
        # Load teams to build lookup
        _ = self.teams_df
        
        edges = []
        
        for _, player in tqdm(
            self.players_df.iterrows(),
            desc="Building played_for_national edges",
            total=len(self.players_df),
        ):
            player_id = player["wiki_id"]
            team_history = self._parse_json_field(player.get("national_team_history"))
            
            for stint in team_history:
                team_name = stint.get("club_name")  # Note: same field name in parser
                if not team_name:
                    continue
                
                team_id = self._match_team_name(team_name)
                
                edges.append({
                    "from_player_id": player_id,
                    "to_team_id": team_id,
                    "to_team_name": team_name,
                    "from_year": stint.get("from_year"),
                    "to_year": stint.get("to_year"),
                    "appearances": stint.get("appearances"),
                    "goals": stint.get("goals"),
                })
        
        df = pd.DataFrame(edges)
        self.stats["played_for_national"] = len(df)
        logger.info(f"Built {len(df)} played_for_national edges")
        
        return df
    
    def build_coached(self) -> pd.DataFrame:
        """
        Build COACHED relationships (coach -> club).
        
        Returns:
            DataFrame with coached edges
        """
        if self.coaches_df.empty:
            return pd.DataFrame()
        
        _ = self.clubs_df
        
        edges = []
        
        for _, coach in tqdm(
            self.coaches_df.iterrows(),
            desc="Building coached edges",
            total=len(self.coaches_df),
        ):
            coach_id = coach["wiki_id"]
            clubs_managed = self._parse_json_field(coach.get("clubs_managed"))
            
            for stint in clubs_managed:
                club_name = stint.get("club_name")
                if not club_name:
                    continue
                
                club_id = self._match_club_name(club_name)
                
                edges.append({
                    "from_coach_id": coach_id,
                    "to_club_id": club_id,
                    "to_club_name": club_name,
                    "from_year": stint.get("from_year"),
                    "to_year": stint.get("to_year"),
                    "role": stint.get("role", "Manager"),
                })
        
        df = pd.DataFrame(edges)
        self.stats["coached"] = len(df)
        logger.info(f"Built {len(df)} coached edges")
        
        return df
    
    def build_coached_national(self) -> pd.DataFrame:
        """
        Build COACHED_NATIONAL relationships (coach -> national_team).
        
        Returns:
            DataFrame with coached_national edges
        """
        if self.coaches_df.empty:
            return pd.DataFrame()
        
        _ = self.teams_df
        
        edges = []
        
        for _, coach in tqdm(
            self.coaches_df.iterrows(),
            desc="Building coached_national edges",
            total=len(self.coaches_df),
        ):
            coach_id = coach["wiki_id"]
            teams_managed = self._parse_json_field(coach.get("national_teams_managed"))
            
            for stint in teams_managed:
                team_name = stint.get("club_name")
                if not team_name:
                    continue
                
                team_id = self._match_team_name(team_name)
                
                edges.append({
                    "from_coach_id": coach_id,
                    "to_team_id": team_id,
                    "to_team_name": team_name,
                    "from_year": stint.get("from_year"),
                    "to_year": stint.get("to_year"),
                    "role": stint.get("role", "Manager"),
                })
        
        df = pd.DataFrame(edges)
        self.stats["coached_national"] = len(df)
        logger.info(f"Built {len(df)} coached_national edges")
        
        return df
    
    def build_teammate(self) -> pd.DataFrame:
        """
        Build TEAMMATE relationships (player <-> player at same club).
        
        Two players are teammates if they played for the same club
        during overlapping time periods.
        
        Returns:
            DataFrame with teammate edges
        """
        if self.players_df.empty:
            return pd.DataFrame()
        
        # Build index: (club_name_normalized) -> list of (player_id, from_year, to_year)
        club_stints: Dict[str, List[Tuple[int, int, int]]] = defaultdict(list)
        
        for _, player in self.players_df.iterrows():
            player_id = player["wiki_id"]
            clubs_history = self._parse_json_field(player.get("clubs_history"))
            
            for stint in clubs_history:
                club_name = stint.get("club_name", "").lower().strip()
                if club_name:
                    from_year = stint.get("from_year") or 1900
                    to_year = stint.get("to_year") or 2025
                    club_stints[club_name].append((player_id, from_year, to_year))
        
        # Generate teammate pairs
        edges = []
        seen_pairs: Set[Tuple[int, int, str]] = set()
        
        for club_name, stints in tqdm(
            club_stints.items(),
            desc="Building teammate edges",
        ):
            if len(stints) < 2:
                continue
            
            # Check all pairs
            for (p1_id, p1_from, p1_to), (p2_id, p2_from, p2_to) in combinations(stints, 2):
                if p1_id == p2_id:
                    continue
                
                # Ensure consistent ordering (smaller id first)
                if p1_id > p2_id:
                    p1_id, p2_id = p2_id, p1_id
                    p1_from, p2_from = p2_from, p1_from
                    p1_to, p2_to = p2_to, p1_to
                
                # Check if already seen
                pair_key = (p1_id, p2_id, club_name)
                if pair_key in seen_pairs:
                    continue
                
                # Check year overlap
                if self._years_overlap(p1_from, p1_to, p2_from, p2_to):
                    overlap_from, overlap_to = self._get_overlap_range(
                        p1_from, p1_to, p2_from, p2_to
                    )
                    
                    club_id = self._match_club_name(club_name)
                    
                    edges.append({
                        "player1_id": p1_id,
                        "player2_id": p2_id,
                        "club_id": club_id,
                        "club_name": club_name,
                        "from_year": overlap_from,
                        "to_year": overlap_to,
                    })
                    
                    seen_pairs.add(pair_key)
        
        df = pd.DataFrame(edges)
        self.stats["teammate"] = len(df)
        logger.info(f"Built {len(df)} teammate edges from {len(club_stints)} clubs")
        
        return df
    
    def build_national_teammate(self) -> pd.DataFrame:
        """
        Build NATIONAL_TEAMMATE relationships (player <-> player at same national team).
        
        Returns:
            DataFrame with national_teammate edges
        """
        if self.players_df.empty:
            return pd.DataFrame()
        
        # Build index: team_name -> list of (player_id, from_year, to_year)
        team_stints: Dict[str, List[Tuple[int, int, int]]] = defaultdict(list)
        
        for _, player in self.players_df.iterrows():
            player_id = player["wiki_id"]
            team_history = self._parse_json_field(player.get("national_team_history"))
            
            for stint in team_history:
                team_name = stint.get("club_name", "").lower().strip()
                if team_name:
                    from_year = stint.get("from_year") or 1900
                    to_year = stint.get("to_year") or 2025
                    team_stints[team_name].append((player_id, from_year, to_year))
        
        # Generate teammate pairs
        edges = []
        seen_pairs: Set[Tuple[int, int, str]] = set()
        
        for team_name, stints in tqdm(
            team_stints.items(),
            desc="Building national_teammate edges",
        ):
            if len(stints) < 2:
                continue
            
            for (p1_id, p1_from, p1_to), (p2_id, p2_from, p2_to) in combinations(stints, 2):
                if p1_id == p2_id:
                    continue
                
                if p1_id > p2_id:
                    p1_id, p2_id = p2_id, p1_id
                    p1_from, p2_from = p2_from, p1_from
                    p1_to, p2_to = p2_to, p1_to
                
                pair_key = (p1_id, p2_id, team_name)
                if pair_key in seen_pairs:
                    continue
                
                if self._years_overlap(p1_from, p1_to, p2_from, p2_to):
                    overlap_from, overlap_to = self._get_overlap_range(
                        p1_from, p1_to, p2_from, p2_to
                    )
                    
                    team_id = self._match_team_name(team_name)
                    
                    edges.append({
                        "player1_id": p1_id,
                        "player2_id": p2_id,
                        "team_id": team_id,
                        "team_name": team_name,
                        "from_year": overlap_from,
                        "to_year": overlap_to,
                    })
                    
                    seen_pairs.add(pair_key)
        
        df = pd.DataFrame(edges)
        self.stats["national_teammate"] = len(df)
        logger.info(f"Built {len(df)} national_teammate edges")
        
        return df
    
    def build_under_coach(self) -> pd.DataFrame:
        """
        Build UNDER_COACH relationships (player -> coach at same club/time).
        
        A player played under a coach if they were at the same club
        during overlapping time periods.
        
        Returns:
            DataFrame with under_coach edges
        """
        if self.players_df.empty or self.coaches_df.empty:
            return pd.DataFrame()
        
        # Build coach index: club_name -> list of (coach_id, from_year, to_year)
        coach_stints: Dict[str, List[Tuple[int, int, int]]] = defaultdict(list)
        
        for _, coach in self.coaches_df.iterrows():
            coach_id = coach["wiki_id"]
            clubs_managed = self._parse_json_field(coach.get("clubs_managed"))
            
            for stint in clubs_managed:
                club_name = stint.get("club_name", "").lower().strip()
                if club_name:
                    from_year = stint.get("from_year") or 1900
                    to_year = stint.get("to_year") or 2025
                    coach_stints[club_name].append((coach_id, from_year, to_year))
        
        # Match players with coaches
        edges = []
        seen: Set[Tuple[int, int, str]] = set()
        
        for _, player in tqdm(
            self.players_df.iterrows(),
            desc="Building under_coach edges",
            total=len(self.players_df),
        ):
            player_id = player["wiki_id"]
            clubs_history = self._parse_json_field(player.get("clubs_history"))
            
            for stint in clubs_history:
                club_name = stint.get("club_name", "").lower().strip()
                if not club_name or club_name not in coach_stints:
                    continue
                
                p_from = stint.get("from_year") or 1900
                p_to = stint.get("to_year") or 2025
                
                for coach_id, c_from, c_to in coach_stints[club_name]:
                    key = (player_id, coach_id, club_name)
                    if key in seen:
                        continue
                    
                    if self._years_overlap(p_from, p_to, c_from, c_to):
                        overlap_from, overlap_to = self._get_overlap_range(
                            p_from, p_to, c_from, c_to
                        )
                        
                        club_id = self._match_club_name(club_name)
                        
                        edges.append({
                            "player_id": player_id,
                            "coach_id": coach_id,
                            "club_id": club_id,
                            "club_name": club_name,
                            "from_year": overlap_from,
                            "to_year": overlap_to,
                        })
                        
                        seen.add(key)
        
        df = pd.DataFrame(edges)
        self.stats["under_coach"] = len(df)
        logger.info(f"Built {len(df)} under_coach edges")
        
        return df
    
    def build_has_position(self) -> pd.DataFrame:
        """
        Build HAS_POSITION relationships (player -> position).
        
        Returns:
            DataFrame with has_position edges
        """
        if self.players_df.empty or self.positions_df.empty:
            return pd.DataFrame()
        
        # Build position lookup
        position_ids = {}
        for _, pos in self.positions_df.iterrows():
            pos_code = pos.get("position_code", pos.get("position_id"))
            position_ids[str(pos_code).upper()] = pos.get("position_id", pos_code)
        
        edges = []
        
        for _, player in self.players_df.iterrows():
            player_id = player["wiki_id"]
            position = player.get("position_normalized")
            
            if pd.isna(position) or not position:
                continue
            
            position_upper = str(position).upper()
            position_id = position_ids.get(position_upper, position_upper)
            
            edges.append({
                "player_id": player_id,
                "position_id": position_id,
            })
        
        df = pd.DataFrame(edges)
        self.stats["has_position"] = len(df)
        logger.info(f"Built {len(df)} has_position edges")
        
        return df
    
    def build_has_nationality(self) -> pd.DataFrame:
        """
        Build HAS_NATIONALITY relationships (player/coach -> nationality).
        
        Returns:
            DataFrame with has_nationality edges
        """
        # Build nationality lookup
        nationality_ids = {}
        if not self.nationalities_df.empty:
            for _, nat in self.nationalities_df.iterrows():
                name = str(nat.get("nationality_name", "")).lower()
                nationality_ids[name] = nat.get("nationality_id")
        
        edges = []
        
        # Players
        for _, player in self.players_df.iterrows():
            player_id = player["wiki_id"]
            nationality = player.get("nationality_normalized")
            
            if pd.isna(nationality) or not nationality:
                continue
            
            nat_lower = str(nationality).lower()
            nat_id = nationality_ids.get(nat_lower, nat_lower)
            
            edges.append({
                "entity_id": player_id,
                "entity_type": "player",
                "nationality_id": nat_id,
                "nationality_name": nationality,
            })
        
        # Coaches
        for _, coach in self.coaches_df.iterrows():
            coach_id = coach["wiki_id"]
            nationality = coach.get("nationality_normalized")
            
            if pd.isna(nationality) or not nationality:
                continue
            
            nat_lower = str(nationality).lower()
            nat_id = nationality_ids.get(nat_lower, nat_lower)
            
            edges.append({
                "entity_id": coach_id,
                "entity_type": "coach",
                "nationality_id": nat_id,
                "nationality_name": nationality,
            })
        
        df = pd.DataFrame(edges)
        self.stats["has_nationality"] = len(df)
        logger.info(f"Built {len(df)} has_nationality edges")
        
        return df
    
    def _match_stadium_name(self, stadium_name: str) -> Optional[int]:
        """Try to match a stadium name to a wiki_id."""
        if not stadium_name:
            return None
        
        # Ensure stadiums are loaded
        _ = self.stadiums_df
        
        if not hasattr(self, '_stadium_name_to_id'):
            return None
        
        name_lower = stadium_name.lower().strip()
        
        # Direct lookup
        if name_lower in self._stadium_name_to_id:
            return self._stadium_name_to_id[name_lower]
        
        # Fuzzy match
        for known_name, wiki_id in self._stadium_name_to_id.items():
            if known_name in name_lower or name_lower in known_name:
                return wiki_id
        
        return None
    
    def build_home_stadium(self) -> pd.DataFrame:
        """
        Build HOME_STADIUM relationships (club -> stadium).
        
        Uses the 'ground' field from clubs to match stadiums.
        
        Returns:
            DataFrame with home_stadium edges
        """
        if self.clubs_df.empty or self.stadiums_df.empty:
            logger.warning("No clubs or stadiums data available")
            return pd.DataFrame()
        
        edges = []
        
        for _, club in tqdm(
            self.clubs_df.iterrows(),
            desc="Building home_stadium edges",
            total=len(self.clubs_df),
        ):
            club_id = club["wiki_id"]
            ground = club.get("ground")
            
            if pd.isna(ground) or not ground:
                continue
            
            stadium_id = self._match_stadium_name(ground)
            
            edges.append({
                "club_id": club_id,
                "stadium_id": stadium_id,
                "stadium_name": ground,
            })
        
        df = pd.DataFrame(edges)
        self.stats["home_stadium"] = len(df)
        logger.info(f"Built {len(df)} home_stadium edges")
        
        return df

    def _load_provinces_df(self) -> pd.DataFrame:
        """Lazy-load provinces DataFrame."""
        if not hasattr(self, '_provinces_df') or self._provinces_df is None:
            self._provinces_df = self._load_csv("provinces_reference.csv")
            # Build name lookup
            if not self._provinces_df.empty:
                if not hasattr(self, '_province_name_to_id'):
                    self._province_name_to_id = {}
                for _, row in self._provinces_df.iterrows():
                    name = str(row.get("name", "")).lower().strip()
                    province_id = row.get("province_id")
                    if name and province_id:
                        self._province_name_to_id[name] = province_id
        return self._provinces_df
    
    def _match_province_name(self, province_name: str) -> Optional[int]:
        """Try to match a province name to a province_id."""
        if not province_name:
            return None
        
        # Ensure provinces are loaded
        _ = self._load_provinces_df()
        
        if not hasattr(self, '_province_name_to_id'):
            return None
        
        name_lower = province_name.lower().strip()
        
        # Direct lookup
        if name_lower in self._province_name_to_id:
            return self._province_name_to_id[name_lower]
        
        # Fuzzy match
        for known_name, province_id in self._province_name_to_id.items():
            if known_name in name_lower or name_lower in known_name:
                return province_id
        
        return None

    def build_stadium_in_province(self) -> pd.DataFrame:
        """
        Build STADIUM_IN_PROVINCE relationships (stadium -> province).
        
        Returns:
            DataFrame with stadium_in_province edges
        """
        if self.stadiums_df.empty:
            logger.warning("No stadiums data available")
            return pd.DataFrame()
        
        _ = self._load_provinces_df()
        
        edges = []
        
        for _, stadium in tqdm(
            self.stadiums_df.iterrows(),
            desc="Building stadium_in_province edges",
            total=len(self.stadiums_df),
        ):
            stadium_id = stadium["wiki_id"]
            province = stadium.get("province")
            
            if pd.isna(province) or not province:
                continue
            
            province_id = self._match_province_name(province)
            
            if province_id:
                edges.append({
                    "stadium_id": stadium_id,
                    "province_id": province_id,
                    "province_name": province,
                })
        
        df = pd.DataFrame(edges)
        self.stats["stadium_in_province"] = len(df)
        logger.info(f"Built {len(df)} stadium_in_province edges")
        
        return df

    def build_club_based_in(self) -> pd.DataFrame:
        """
        Build CLUB_BASED_IN relationships (club -> province).
        
        Derives the province from the club's home stadium.
        
        Returns:
            DataFrame with club_based_in edges
        """
        if self.clubs_df.empty:
            logger.warning("No clubs data available")
            return pd.DataFrame()
        
        _ = self.stadiums_df
        _ = self._load_provinces_df()
        
        # Build stadium -> province mapping
        stadium_province_map = {}
        if not self.stadiums_df.empty:
            for _, stadium in self.stadiums_df.iterrows():
                province = stadium.get("province")
                if province and not pd.isna(province):
                    stadium_name = str(stadium.get("name", "")).lower().strip()
                    stadium_province_map[stadium_name] = province
        
        edges = []
        
        for _, club in tqdm(
            self.clubs_df.iterrows(),
            desc="Building club_based_in edges",
            total=len(self.clubs_df),
        ):
            club_id = club["wiki_id"]
            ground = club.get("ground")
            
            if pd.isna(ground) or not ground:
                continue
            
            ground_lower = ground.lower().strip()
            
            # Find province from stadium
            province = None
            for stadium_name, prov in stadium_province_map.items():
                if stadium_name in ground_lower or ground_lower in stadium_name:
                    province = prov
                    break
            
            if province:
                province_id = self._match_province_name(province)
                if province_id:
                    edges.append({
                        "club_id": club_id,
                        "province_id": province_id,
                        "province_name": province,
                    })
        
        df = pd.DataFrame(edges)
        self.stats["club_based_in"] = len(df)
        logger.info(f"Built {len(df)} club_based_in edges")
        
        return df

    def build_competes_in(self) -> pd.DataFrame:
        """
        Build COMPETES_IN relationships (club -> competition).
        
        Uses the 'league' field from clubs.
        
        Returns:
            DataFrame with competes_in edges
        """
        if self.clubs_df.empty:
            logger.warning("No clubs data available")
            return pd.DataFrame()
        
        # Build competition name lookup
        competition_name_to_id = {}
        if not self.competitions_df.empty:
            for _, comp in self.competitions_df.iterrows():
                name = str(comp.get("name", "")).lower().strip()
                wiki_id = comp.get("wiki_id")
                if name and wiki_id:
                    competition_name_to_id[name] = wiki_id
        
        edges = []
        
        for _, club in tqdm(
            self.clubs_df.iterrows(),
            desc="Building competes_in edges",
            total=len(self.clubs_df),
        ):
            club_id = club["wiki_id"]
            league = club.get("league")
            
            if pd.isna(league) or not league:
                continue
            
            league_lower = league.lower().strip()
            
            # Try to match competition
            comp_id = None
            for comp_name, cid in competition_name_to_id.items():
                if comp_name in league_lower or league_lower in comp_name:
                    comp_id = cid
                    break
            
            edges.append({
                "club_id": club_id,
                "competition_id": comp_id,
                "competition_name": league,
            })
        
        df = pd.DataFrame(edges)
        self.stats["competes_in"] = len(df)
        logger.info(f"Built {len(df)} competes_in edges")
        
        return df

    def build_same_province_clubs(self) -> pd.DataFrame:
        """
        Build SAME_PROVINCE (derby/rivals) relationships (club <-> club).
        
        Two clubs are in the same province if they have the same home province.
        This creates potential derby/rivalry relationships.
        
        Returns:
            DataFrame with same_province edges
        """
        if self.clubs_df.empty:
            logger.warning("No clubs data available")
            return pd.DataFrame()
        
        _ = self.stadiums_df
        
        # Build stadium -> province mapping
        stadium_province_map = {}
        if not self.stadiums_df.empty:
            for _, stadium in self.stadiums_df.iterrows():
                province = stadium.get("province")
                if province and not pd.isna(province):
                    stadium_name = str(stadium.get("name", "")).lower().strip()
                    stadium_province_map[stadium_name] = province
        
        # Build club -> province mapping
        club_provinces: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        
        for _, club in self.clubs_df.iterrows():
            club_id = club["wiki_id"]
            club_name = club.get("name", "")
            ground = club.get("ground")
            
            if pd.isna(ground) or not ground:
                continue
            
            ground_lower = ground.lower().strip()
            
            for stadium_name, province in stadium_province_map.items():
                if stadium_name in ground_lower or ground_lower in stadium_name:
                    club_provinces[province].append((club_id, club_name))
                    break
        
        # Generate same-province pairs
        edges = []
        
        for province, clubs in club_provinces.items():
            if len(clubs) < 2:
                continue
            
            for (c1_id, c1_name), (c2_id, c2_name) in combinations(clubs, 2):
                # Ensure consistent ordering
                if c1_id > c2_id:
                    c1_id, c2_id = c2_id, c1_id
                    c1_name, c2_name = c2_name, c1_name
                
                province_id = self._match_province_name(province)
                
                edges.append({
                    "club1_id": c1_id,
                    "club1_name": c1_name,
                    "club2_id": c2_id,
                    "club2_name": c2_name,
                    "province_id": province_id,
                    "province_name": province,
                })
        
        df = pd.DataFrame(edges)
        self.stats["same_province"] = len(df)
        logger.info(f"Built {len(df)} same_province edges (potential derbies)")
        
        return df

    def build_player_from_province(self) -> pd.DataFrame:
        """
        Build PLAYER_FROM_PROVINCE relationships (player -> province based on birthplace).
        
        This enhances the born_in relationship to include province info directly.
        
        Returns:
            DataFrame with player_from_province edges
        """
        # Load players with Vietnam nationality
        players_file = PROCESSED_DATA_DIR / "players_vn_clean.csv"
        if not players_file.exists():
            logger.warning("No players_vn_clean.csv found")
            return pd.DataFrame()
        
        players_df = pd.read_csv(players_file, encoding="utf-8")
        _ = self._load_provinces_df()
        
        edges = []
        
        for _, player in tqdm(
            players_df.iterrows(),
            desc="Building player_from_province edges",
            total=len(players_df),
        ):
            player_id = player["wiki_id"]
            province = player.get("province")
            
            if pd.isna(province) or not province:
                continue
            
            province_id = self._match_province_name(province)
            
            if province_id:
                edges.append({
                    "player_id": player_id,
                    "province_id": province_id,
                    "province_name": province,
                })
        
        df = pd.DataFrame(edges)
        self.stats["player_from_province"] = len(df)
        logger.info(f"Built {len(df)} player_from_province edges")
        
        return df

    def build_played_same_club(self) -> pd.DataFrame:
        """
        Build PLAYED_SAME_CLUB relationships (more detailed than teammate).
        
        Shows all clubs where two players have both played (may not overlap in time).
        This is useful for finding transfer patterns.
        
        Returns:
            DataFrame with played_same_club edges
        """
        if self.players_df.empty:
            return pd.DataFrame()
        
        # Build index: club -> set of player ids
        club_players: Dict[str, Set[int]] = defaultdict(set)
        
        for _, player in self.players_df.iterrows():
            player_id = player["wiki_id"]
            clubs_history = self._parse_json_field(player.get("clubs_history"))
            
            for stint in clubs_history:
                club_name = stint.get("club_name", "").lower().strip()
                if club_name:
                    club_players[club_name].add(player_id)
        
        # Find players who played for multiple same clubs
        player_clubs: Dict[int, Set[str]] = defaultdict(set)
        for club, players in club_players.items():
            for pid in players:
                player_clubs[pid].add(club)
        
        # Generate pairs with shared clubs
        edges = []
        seen_pairs: Set[Tuple[int, int]] = set()
        
        player_ids = list(player_clubs.keys())
        
        for i, p1_id in enumerate(tqdm(player_ids, desc="Building played_same_club edges")):
            for p2_id in player_ids[i+1:]:
                shared_clubs = player_clubs[p1_id] & player_clubs[p2_id]
                
                if len(shared_clubs) >= 2:  # Only include if shared 2+ clubs
                    if p1_id > p2_id:
                        p1_id, p2_id = p2_id, p1_id
                    
                    pair_key = (p1_id, p2_id)
                    if pair_key not in seen_pairs:
                        edges.append({
                            "player1_id": p1_id,
                            "player2_id": p2_id,
                            "shared_clubs_count": len(shared_clubs),
                            "shared_clubs": "|".join(sorted(shared_clubs)),
                        })
                        seen_pairs.add(pair_key)
        
        df = pd.DataFrame(edges)
        self.stats["played_same_club"] = len(df)
        logger.info(f"Built {len(df)} played_same_club edges (players who shared 2+ clubs)")
        
        return df
    
    def save_edges(
        self,
        df: pd.DataFrame,
        edge_type: str,
    ) -> Path:
        """
        Save edge DataFrame to CSV.
        
        Args:
            df: Edge DataFrame
            edge_type: Type of edge
            
        Returns:
            Path to saved file
        """
        if df.empty:
            logger.warning(f"No edges to save for {edge_type}")
            return None
        
        output_path = get_edge_file_path(edge_type)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} {edge_type} edges to {output_path}")
        
        return output_path
    
    def build_all(self) -> Dict[str, pd.DataFrame]:
        """
        Build all relationship types.
        
        Returns:
            Dictionary mapping edge type to DataFrame
        """
        results = {}
        
        # LAYER 1: Direct relationships
        logger.info("\n" + "=" * 60)
        logger.info("LAYER 1: Building direct relationships")
        logger.info("=" * 60)
        
        layer1 = [
            ("played_for", self.build_played_for),
            ("played_for_national", self.build_played_for_national),
            ("coached", self.build_coached),
            ("coached_national", self.build_coached_national),
        ]
        
        for edge_type, builder in layer1:
            df = builder()
            if not df.empty:
                self.save_edges(df, edge_type)
                results[edge_type] = df
        
        # LAYER 2: Derived relationships
        logger.info("\n" + "=" * 60)
        logger.info("LAYER 2: Building derived relationships")
        logger.info("=" * 60)
        
        layer2 = [
            ("teammate", self.build_teammate),
            ("national_teammate", self.build_national_teammate),
            ("under_coach", self.build_under_coach),
        ]
        
        for edge_type, builder in layer2:
            df = builder()
            if not df.empty:
                self.save_edges(df, edge_type)
                results[edge_type] = df
        
        # LAYER 3: Semantic relationships
        logger.info("\n" + "=" * 60)
        logger.info("LAYER 3: Building semantic relationships")
        logger.info("=" * 60)
        
        layer3 = [
            ("has_position", self.build_has_position),
            ("has_nationality", self.build_has_nationality),
            ("home_stadium", self.build_home_stadium),
            ("stadium_in_province", self.build_stadium_in_province),
            ("club_based_in", self.build_club_based_in),
            ("competes_in", self.build_competes_in),
            ("same_province", self.build_same_province_clubs),
            ("player_from_province", self.build_player_from_province),
            ("played_same_club", self.build_played_same_club),
        ]
        
        for edge_type, builder in layer3:
            df = builder()
            if not df.empty:
                self.save_edges(df, edge_type)
                results[edge_type] = df
        
        # Print summary
        self._print_summary()
        
        return results
    
    def _print_summary(self) -> None:
        """Print relationship building summary."""
        print("\n" + "=" * 60)
        print("RELATIONSHIP BUILDING SUMMARY")
        print("=" * 60)
        
        total = 0
        for edge_type, count in self.stats.items():
            print(f"  {edge_type}: {count} edges")
            total += count
        
        print("-" * 60)
        print(f"  TOTAL: {total} edges")
        print("=" * 60)


def main():
    """Main entry point for the relationship builder CLI."""
    parser = argparse.ArgumentParser(
        description="Build relationship tables for the knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Build all relationships:
    python -m processor.relationship_builder --build-all
    
  Build specific relationship:
    python -m processor.relationship_builder --build played_for
    python -m processor.relationship_builder --build teammate
        """,
    )
    
    parser.add_argument(
        "--build-all",
        action="store_true",
        help="Build all relationship types",
    )
    parser.add_argument(
        "--build",
        type=str,
        choices=[
            "played_for", "played_for_national",
            "coached", "coached_national",
            "teammate", "national_teammate", "under_coach",
            "has_position", "has_nationality",
        ],
        help="Build a specific relationship type",
    )
    
    args = parser.parse_args()
    
    if not args.build_all and not args.build:
        parser.error("Must specify --build-all or --build")
    
    builder = RelationshipBuilder()
    
    if args.build_all:
        builder.build_all()
    elif args.build:
        builders = {
            "played_for": builder.build_played_for,
            "played_for_national": builder.build_played_for_national,
            "coached": builder.build_coached,
            "coached_national": builder.build_coached_national,
            "teammate": builder.build_teammate,
            "national_teammate": builder.build_national_teammate,
            "under_coach": builder.build_under_coach,
            "has_position": builder.build_has_position,
            "has_nationality": builder.build_has_nationality,
        }
        
        df = builders[args.build]()
        if not df.empty:
            builder.save_edges(df, args.build)
            print(f"\nBuilt {len(df)} {args.build} edges")
        else:
            print(f"\nNo edges built for {args.build}")


if __name__ == "__main__":
    main()
