"""
Infobox Parser for Vietnamese Football Knowledge Graph

This module parses wikitext from raw JSON files to extract structured data
from infoboxes for players, coaches, clubs, and national teams.

Features:
- Parses various infobox templates (Vietnamese and English)
- Extracts career history (clubs, national teams)
- Normalizes entity names
- Handles missing fields gracefully
- Outputs JSONL files for easy incremental loading

Usage:
    python -m parser.infobox_parser --parse-all
    python -m parser.infobox_parser --entity-type player
    python -m parser.infobox_parser --file data/raw/player_12345.json
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import mwparserfromhell
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    ENTITY_TYPES,
    FIELD_MAPPINGS,
    INFOBOX_TEMPLATES,
    POSITION_MAPPINGS,
    RAW_DATA_DIR,
    get_parsed_file_path,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class InfoboxParser:
    """
    Parser for Wikipedia infoboxes to extract structured data.
    
    Handles various infobox templates for players, coaches, clubs, and teams.
    """
    
    def __init__(self):
        """Initialize the parser."""
        self.stats = {
            "total": 0,
            "success": 0,
            "no_infobox": 0,
            "parse_error": 0,
        }
    
    def reset_stats(self):
        """Reset parsing statistics."""
        self.stats = {
            "total": 0,
            "success": 0,
            "no_infobox": 0,
            "parse_error": 0,
        }
    
    def _normalize_field_name(self, field_name: str) -> str:
        """
        Normalize a field name to standard English.
        
        Args:
            field_name: Raw field name from infobox
            
        Returns:
            Normalized field name
        """
        # Clean up the field name
        field_name = field_name.strip().lower()
        field_name = re.sub(r'\s+', '_', field_name)
        
        # Check mappings
        if field_name in FIELD_MAPPINGS:
            return FIELD_MAPPINGS[field_name]
        
        # Remove underscores for comparison
        field_no_underscore = field_name.replace('_', ' ')
        if field_no_underscore in FIELD_MAPPINGS:
            return FIELD_MAPPINGS[field_no_underscore]
        
        return field_name
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize an entity name by removing nicknames and extra whitespace.
        
        Args:
            name: Raw name string
            
        Returns:
            Normalized name
        """
        if not name:
            return name
        
        # Remove content in parentheses (nicknames)
        name = re.sub(r'\s*\([^)]*\)\s*', '', name)
        
        # Remove wiki markup
        name = re.sub(r'\[\[([^\]|]*)\|?([^\]]*)\]\]', r'\2' if r'\2' else r'\1', name)
        name = re.sub(r'\[\[|\]\]', '', name)
        
        # Remove HTML tags
        name = re.sub(r'<[^>]+>', '', name)
        
        # Normalize whitespace
        name = ' '.join(name.split())
        
        return name.strip()
    
    def _clean_wikitext(self, text: str) -> str:
        """
        Clean wikitext markup from a string.
        
        Args:
            text: Raw wikitext string
            
        Returns:
            Cleaned plain text
        """
        if not text:
            return text
        
        # Remove references
        text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
        text = re.sub(r'<ref[^/]*/>', '', text)
        
        # Extract text from wiki links
        text = re.sub(r'\[\[([^\]|]*)\|([^\]]*)\]\]', r'\2', text)
        text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
        
        # Remove templates (basic)
        text = re.sub(r'\{\{[^{}]*\}\}', '', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _extract_date(self, date_str: str) -> Optional[str]:
        """
        Extract and normalize a date string.
        
        Args:
            date_str: Raw date string from infobox
            
        Returns:
            Normalized date string (YYYY-MM-DD) or None
        """
        if not date_str:
            return None
        
        # Clean the string first
        date_str = self._clean_wikitext(date_str)
        
        # Try to extract date from birth date templates
        # {{birth date and age|1990|3|15}} or {{Birth date|df=yes|1990|3|15}}
        match = re.search(r'(\d{4})\|(\d{1,2})\|(\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        # Try standard date formats
        # YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        # DD Month YYYY or Month DD, YYYY
        months_vi = {
            'tháng 1': '01', 'tháng 2': '02', 'tháng 3': '03',
            'tháng 4': '04', 'tháng 5': '05', 'tháng 6': '06',
            'tháng 7': '07', 'tháng 8': '08', 'tháng 9': '09',
            'tháng 10': '10', 'tháng 11': '11', 'tháng 12': '12',
        }
        months_en = {
            'january': '01', 'february': '02', 'march': '03',
            'april': '04', 'may': '05', 'june': '06',
            'july': '07', 'august': '08', 'september': '09',
            'october': '10', 'november': '11', 'december': '12',
        }
        
        date_lower = date_str.lower()
        for month_name, month_num in {**months_vi, **months_en}.items():
            if month_name in date_lower:
                # Try to find day and year
                numbers = re.findall(r'\d+', date_str)
                if len(numbers) >= 2:
                    # Assume first is day, last is year (if year > 1900)
                    for num in numbers:
                        if int(num) > 1900:
                            year = num
                            day = numbers[0] if numbers[0] != year else numbers[1]
                            return f"{year}-{month_num}-{int(day):02d}"
        
        # Just try to find a year
        match = re.search(r'\b(19\d{2}|20\d{2})\b', date_str)
        if match:
            return f"{match.group(1)}-01-01"  # Default to January 1
        
        return None
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract a year from text."""
        if not text:
            return None
        match = re.search(r'\b(19\d{2}|20\d{2})\b', str(text))
        return int(match.group(1)) if match else None
    
    def _parse_year_range(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse a year range like "2010-2015" or "2010–present".
        
        Returns:
            Tuple of (from_year, to_year)
        """
        if not text:
            return None, None
        
        text = self._clean_wikitext(str(text))
        
        # Handle "present", "nay", "hiện tại"
        is_present = any(word in text.lower() for word in ['present', 'nay', 'hiện tại', 'current'])
        
        # Find all years
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        
        if len(years) >= 2:
            return int(years[0]), int(years[1])
        elif len(years) == 1:
            if is_present:
                return int(years[0]), None  # None means present/ongoing
            return int(years[0]), int(years[0])
        
        return None, None
    
    def _normalize_position(self, position: str) -> str:
        """
        Normalize a position string to standard code.
        
        Args:
            position: Raw position string
            
        Returns:
            Normalized position code (e.g., "GK", "CB", "MF")
        """
        if not position:
            return position
        
        position_lower = position.lower().strip()
        
        # Check direct mappings
        if position_lower in POSITION_MAPPINGS:
            return POSITION_MAPPINGS[position_lower]
        
        # Check if any mapping key is contained in the position
        for key, code in POSITION_MAPPINGS.items():
            if key in position_lower:
                return code
        
        return position.upper()[:3]  # Fallback: first 3 chars
    
    def _find_infobox(
        self,
        wikicode: mwparserfromhell.wikicode.Wikicode,
        entity_type: str,
    ) -> Optional[mwparserfromhell.nodes.Template]:
        """
        Find the main infobox template in wikicode.
        
        Args:
            wikicode: Parsed wikicode object
            entity_type: Type of entity to look for
            
        Returns:
            Template object if found, None otherwise
        """
        templates = wikicode.filter_templates()
        
        # Get template names for this entity type
        target_names = INFOBOX_TEMPLATES.get(entity_type, [])
        target_names_lower = [name.lower() for name in target_names]
        
        for template in templates:
            template_name = str(template.name).strip().lower()
            
            # Check exact match
            if template_name in target_names_lower:
                return template
            
            # Check partial match (for variations)
            if any(target in template_name for target in ['infobox', 'thông tin']):
                if any(keyword in template_name for keyword in ['football', 'bóng đá', 'cầu thủ', 'coach', 'club']):
                    return template
        
        return None
    
    def _extract_infobox_params(
        self,
        template: mwparserfromhell.nodes.Template,
    ) -> Dict[str, str]:
        """
        Extract all parameters from an infobox template.
        
        Args:
            template: Infobox template object
            
        Returns:
            Dictionary of normalized field names to values
        """
        params = {}
        
        for param in template.params:
            name = str(param.name).strip()
            value = str(param.value).strip()
            
            if value:
                normalized_name = self._normalize_field_name(name)
                params[normalized_name] = value
                # Also keep original for numbered params
                params[name] = value
        
        return params
    
    def _parse_career_history(
        self,
        params: Dict[str, str],
        prefix: str = "clubs",
    ) -> List[Dict[str, Any]]:
        """
        Parse career history (clubs or national teams) from numbered params.
        
        Args:
            params: Infobox parameters
            prefix: Prefix for career fields (clubs, nationalteam, etc.)
            
        Returns:
            List of career entries
        """
        history = []
        
        # Try different numbering patterns
        for i in range(1, 20):  # Max 20 career entries
            entry = {}
            
            # Try various field patterns
            patterns = [
                (f"{prefix}{i}", "club_name"),
                (f"{prefix}_{i}", "club_name"),
                (f"years{i}", "years"),
                (f"years_{i}", "years"),
                (f"caps{i}", "appearances"),
                (f"caps_{i}", "appearances"),
                (f"goals{i}", "goals"),
                (f"goals_{i}", "goals"),
            ]
            
            for param_name, field_name in patterns:
                if param_name in params:
                    entry[field_name] = params[param_name]
            
            # Also try youthclubs, seniorclubs patterns
            youth_patterns = [
                (f"youthclubs{i}", "club_name"),
                (f"youthyears{i}", "years"),
            ]
            senior_patterns = [
                (f"clubs{i}", "club_name"),
                (f"years{i}", "years"),
                (f"caps{i}", "appearances"),
                (f"goals{i}", "goals"),
            ]
            
            if entry.get("club_name"):
                # Parse years
                if "years" in entry:
                    from_year, to_year = self._parse_year_range(entry["years"])
                    entry["from_year"] = from_year
                    entry["to_year"] = to_year
                    del entry["years"]
                
                # Clean club name
                entry["club_name"] = self._normalize_name(entry["club_name"])
                
                # Parse numeric fields
                for field in ["appearances", "goals"]:
                    if field in entry:
                        try:
                            entry[field] = int(re.sub(r'[^\d]', '', entry[field]) or 0)
                        except ValueError:
                            entry[field] = None
                
                history.append(entry)
        
        # Also try the simple numbered pattern for clubs
        # clubs1, clubs2, etc.
        if not history:
            for key, value in params.items():
                match = re.match(rf'{prefix}(\d+)$', key)
                if match:
                    idx = match.group(1)
                    entry = {
                        "club_name": self._normalize_name(value),
                        "from_year": None,
                        "to_year": None,
                        "appearances": None,
                        "goals": None,
                    }
                    
                    # Try to find corresponding years, caps, goals
                    if f"years{idx}" in params:
                        from_year, to_year = self._parse_year_range(params[f"years{idx}"])
                        entry["from_year"] = from_year
                        entry["to_year"] = to_year
                    
                    if f"caps{idx}" in params:
                        try:
                            entry["appearances"] = int(re.sub(r'[^\d]', '', params[f"caps{idx}"]) or 0)
                        except ValueError:
                            pass
                    
                    if f"goals{idx}" in params:
                        try:
                            entry["goals"] = int(re.sub(r'[^\d]', '', params[f"goals{idx}"]) or 0)
                        except ValueError:
                            pass
                    
                    if entry["club_name"]:
                        history.append(entry)
        
        return history
    
    def parse_player(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse player data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed player data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "player")
            
            if not infobox:
                return None
            
            params = self._extract_infobox_params(infobox)
            
            # Extract basic info
            player = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(
                    params.get("name") or params.get("full_name") or raw_data["page_title"]
                ),
                "full_name": self._normalize_name(params.get("full_name") or params.get("fullname")),
                "date_of_birth": self._extract_date(params.get("date_of_birth") or params.get("birth_date")),
                "place_of_birth": self._clean_wikitext(params.get("place_of_birth") or params.get("birth_place")),
                "nationality": self._clean_wikitext(params.get("nationality")),
                "position": self._normalize_position(
                    self._clean_wikitext(params.get("position") or params.get("vị_trí"))
                ),
                "height": self._clean_wikitext(params.get("height")),
                "current_club": self._normalize_name(
                    params.get("current_club") or params.get("currentclub")
                ),
            }
            
            # Parse career history
            player["clubs_history"] = self._parse_career_history(params, "clubs")
            player["national_team_history"] = self._parse_career_history(params, "nationalteam")
            
            # If no history parsed, try alternate patterns
            if not player["clubs_history"]:
                player["clubs_history"] = self._parse_career_history(params, "club")
            
            return player
            
        except Exception as e:
            logger.warning(f"Error parsing player {raw_data.get('page_title')}: {e}")
            return None
    
    def parse_coach(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse coach data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed coach data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "coach")
            
            if not infobox:
                # Coaches might use player infobox
                infobox = self._find_infobox(wikicode, "player")
                if not infobox:
                    return None
            
            params = self._extract_infobox_params(infobox)
            
            coach = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(
                    params.get("name") or params.get("full_name") or raw_data["page_title"]
                ),
                "full_name": self._normalize_name(params.get("full_name") or params.get("fullname")),
                "date_of_birth": self._extract_date(params.get("date_of_birth") or params.get("birth_date")),
                "nationality": self._clean_wikitext(params.get("nationality")),
            }
            
            # Parse managed clubs history
            coach["clubs_managed"] = self._parse_career_history(params, "managerclubs")
            if not coach["clubs_managed"]:
                coach["clubs_managed"] = self._parse_career_history(params, "manager_clubs")
            
            # Parse national teams managed
            coach["national_teams_managed"] = self._parse_career_history(params, "managernationalteam")
            
            return coach
            
        except Exception as e:
            logger.warning(f"Error parsing coach {raw_data.get('page_title')}: {e}")
            return None
    
    def parse_club(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse club data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed club data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "club")
            
            if not infobox:
                return None
            
            params = self._extract_infobox_params(infobox)
            
            club = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(
                    params.get("clubname") or params.get("name") or raw_data["page_title"]
                ),
                "full_name": self._normalize_name(params.get("fullname") or params.get("full_name")),
                "founded": self._extract_year(params.get("founded") or params.get("thành_lập")),
                "ground": self._clean_wikitext(params.get("ground") or params.get("stadium")),
                "capacity": self._clean_wikitext(params.get("capacity")),
                "chairman": self._normalize_name(params.get("chairman") or params.get("owner")),
                "manager": self._normalize_name(params.get("manager") or params.get("head_coach")),
                "league": self._clean_wikitext(params.get("league")),
                "country": self._clean_wikitext(params.get("country") or "Vietnam"),
            }
            
            return club
            
        except Exception as e:
            logger.warning(f"Error parsing club {raw_data.get('page_title')}: {e}")
            return None
    
    def parse_national_team(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse national team data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed national team data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "national_team")
            
            if not infobox:
                # Try club infobox as fallback
                infobox = self._find_infobox(wikicode, "club")
                if not infobox:
                    return None
            
            params = self._extract_infobox_params(infobox)
            
            # Determine team level (senior, U23, U19, etc.)
            title = raw_data["page_title"].lower()
            level = "senior"
            if "u23" in title or "u-23" in title:
                level = "U23"
            elif "u22" in title or "u-22" in title:
                level = "U22"
            elif "u21" in title or "u-21" in title:
                level = "U21"
            elif "u20" in title or "u-20" in title:
                level = "U20"
            elif "u19" in title or "u-19" in title:
                level = "U19"
            elif "nữ" in title or "women" in title.lower():
                level = "women"
            
            team = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(
                    params.get("name") or raw_data["page_title"]
                ),
                "country_code": "VN",
                "level": level,
                "manager": self._normalize_name(params.get("manager") or params.get("head_coach")),
                "confederation": self._clean_wikitext(params.get("confederation") or "AFC"),
            }
            
            return team
            
        except Exception as e:
            logger.warning(f"Error parsing national team {raw_data.get('page_title')}: {e}")
            return None
    
    def parse_stadium(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse stadium data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed stadium data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "stadium")
            
            if not infobox:
                # Try to extract basic info from page title
                pass
            
            params = self._extract_infobox_params(infobox) if infobox else {}
            
            # Parse capacity - extract just the number
            capacity_str = params.get("capacity") or params.get("sức_chứa") or params.get("sức chứa")
            capacity = None
            if capacity_str:
                capacity_match = re.search(r'[\d,\.]+', capacity_str.replace(',', '').replace('.', ''))
                if capacity_match:
                    try:
                        capacity = int(capacity_match.group().replace(',', '').replace('.', ''))
                    except ValueError:
                        pass
            
            stadium = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(
                    params.get("name") or params.get("stadium_name") or raw_data["page_title"]
                ),
                "location": self._clean_wikitext(
                    params.get("location") or params.get("địa_điểm") or params.get("address")
                ),
                "capacity": capacity,
                "surface": self._clean_wikitext(params.get("surface") or params.get("mặt_sân")),
                "opened": self._extract_year(params.get("opened") or params.get("khai_trương")),
                "owner": self._clean_wikitext(params.get("owner") or params.get("chủ_sở_hữu")),
            }
            
            # Try to extract home team from tenants/clubs field
            tenants = params.get("tenants") or params.get("clubs") or params.get("đội_sân_nhà")
            if tenants:
                stadium["home_teams"] = [self._normalize_name(t) for t in re.split(r'[,\n]', tenants) if t.strip()]
            else:
                stadium["home_teams"] = []
            
            return stadium
            
        except Exception as e:
            logger.warning(f"Error parsing stadium {raw_data.get('page_title')}: {e}")
            return None
    
    def parse_competition(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse competition/league data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed competition data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "competition")
            
            params = self._extract_infobox_params(infobox) if infobox else {}
            
            # Determine competition type from title
            title = raw_data["page_title"].lower()
            comp_type = "league"
            if "cúp" in title or "cup" in title:
                comp_type = "cup"
            elif "siêu" in title or "super" in title:
                comp_type = "super_cup"
            elif "u-" in title or "u16" in title or "u19" in title or "u21" in title:
                comp_type = "youth"
            elif "nữ" in title or "women" in title:
                comp_type = "women"
            
            competition = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(
                    params.get("name") or params.get("competition") or raw_data["page_title"]
                ),
                "competition_type": comp_type,
                "country": "Vietnam",
                "founded": self._extract_year(params.get("founded") or params.get("thành_lập")),
                "teams": self._clean_wikitext(params.get("teams") or params.get("số_đội")),
                "level": self._clean_wikitext(params.get("level") or params.get("cấp_độ")),
                "current_champion": self._normalize_name(params.get("current_champion") or params.get("vô_địch_hiện_tại")),
                "most_titles": self._normalize_name(params.get("most_titles") or params.get("đội_vô_địch_nhiều_nhất")),
            }
            
            return competition
            
        except Exception as e:
            logger.warning(f"Error parsing competition {raw_data.get('page_title')}: {e}")
            return None
    
    def parse_season(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse season data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed season data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "season")
            
            if not infobox:
                infobox = self._find_infobox(wikicode, "competition")
            
            params = self._extract_infobox_params(infobox) if infobox else {}
            
            # Extract year from title
            title = raw_data["page_title"]
            year_match = re.search(r'(\d{4})(?:\s*[-–]\s*(\d{2,4}))?', title)
            year = None
            season_years = None
            if year_match:
                year = int(year_match.group(1))
                if year_match.group(2):
                    end_year = year_match.group(2)
                    if len(end_year) == 2:
                        end_year = str(year)[:2] + end_year
                    season_years = f"{year}-{end_year}"
                else:
                    season_years = str(year)
            
            # Determine parent competition
            parent_comp = None
            if "cúp quốc gia" in title.lower():
                parent_comp = "Giải bóng đá Cúp Quốc gia Việt Nam"
            elif "vô địch quốc gia" in title.lower() or "v.league" in title.lower():
                parent_comp = "Giải bóng đá Vô địch Quốc gia Việt Nam"
            elif "hạng nhất" in title.lower():
                parent_comp = "Giải bóng đá hạng Nhất Quốc gia Việt Nam"
            elif "siêu cúp" in title.lower():
                parent_comp = "Siêu cúp bóng đá Việt Nam"
            
            season = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(raw_data["page_title"]),
                "year": year,
                "season_years": season_years,
                "parent_competition": parent_comp,
                "champion": self._normalize_name(params.get("winners") or params.get("champion") or params.get("vô_địch")),
                "runner_up": self._normalize_name(params.get("runner-up") or params.get("á_quân")),
                "top_scorer": self._clean_wikitext(params.get("top_scorer") or params.get("vua_phá_lưới")),
                "teams": self._clean_wikitext(params.get("teams") or params.get("số_đội")),
            }
            
            return season
            
        except Exception as e:
            logger.warning(f"Error parsing season {raw_data.get('page_title')}: {e}")
            return None
    
    def parse_award(
        self,
        raw_data: Dict,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse award data from raw page data.
        
        Args:
            raw_data: Raw page data with wikitext
            
        Returns:
            Parsed award data or None
        """
        try:
            wikicode = mwparserfromhell.parse(raw_data["wikitext"])
            infobox = self._find_infobox(wikicode, "award")
            
            # For Quả bóng vàng winners (which are player pages)
            # We extract info differently
            params = self._extract_infobox_params(infobox) if infobox else {}
            
            # Determine award type from title
            title = raw_data["page_title"].lower()
            award_type = "other"
            if "quả bóng vàng" in title:
                award_type = "golden_ball"
            elif "vua phá lưới" in title or "chiếc giày" in title:
                award_type = "golden_boot"
            elif "cầu thủ xuất sắc" in title:
                award_type = "best_player"
            elif "huấn luyện viên xuất sắc" in title:
                award_type = "best_coach"
            elif "fair play" in title:
                award_type = "fair_play"
            
            award = {
                "wiki_id": raw_data["page_id"],
                "wiki_url": raw_data["full_url"],
                "wiki_title": raw_data["page_title"],
                "name": self._normalize_name(
                    params.get("name") or raw_data["page_title"]
                ),
                "award_type": award_type,
                "country": "Vietnam",
            }
            
            return award
            
        except Exception as e:
            logger.warning(f"Error parsing award {raw_data.get('page_title')}: {e}")
            return None

    def parse_file(
        self,
        file_path: Path,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single raw JSON file.
        
        Args:
            file_path: Path to raw JSON file
            
        Returns:
            Parsed data or None
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return None
        
        entity_type = raw_data.get("entity_type", "")
        
        # Route to appropriate parser
        parsers = {
            "player": self.parse_player,
            "coach": self.parse_coach,
            "club": self.parse_club,
            "national_team": self.parse_national_team,
            "stadium": self.parse_stadium,
            "competition": self.parse_competition,
            "season": self.parse_season,
            "award": self.parse_award,
        }
        
        parser_func = parsers.get(entity_type)
        if not parser_func:
            logger.warning(f"Unknown entity type: {entity_type}")
            return None
        
        return parser_func(raw_data)
    
    def parse_all_by_type(
        self,
        entity_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse all raw files of a given entity type.
        
        Args:
            entity_type: Type of entity to parse
            
        Returns:
            List of parsed entities
        """
        # Find all files for this entity type
        pattern = f"{entity_type}_*.json"
        files = list(RAW_DATA_DIR.glob(pattern))
        
        if not files:
            logger.warning(f"No files found for entity type: {entity_type}")
            return []
        
        logger.info(f"Found {len(files)} {entity_type} files to parse")
        
        parsed_entities = []
        
        for file_path in tqdm(files, desc=f"Parsing {entity_type}s", unit="file"):
            self.stats["total"] += 1
            
            result = self.parse_file(file_path)
            
            if result:
                parsed_entities.append(result)
                self.stats["success"] += 1
            else:
                # Check if it was a parsing error or just no infobox
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                    wikicode = mwparserfromhell.parse(raw_data["wikitext"])
                    infobox = self._find_infobox(wikicode, entity_type)
                    if infobox is None:
                        self.stats["no_infobox"] += 1
                    else:
                        self.stats["parse_error"] += 1
                except Exception:
                    self.stats["parse_error"] += 1
        
        return parsed_entities
    
    def save_parsed_data(
        self,
        entities: List[Dict[str, Any]],
        entity_type: str,
    ) -> Path:
        """
        Save parsed entities to JSONL file.
        
        Args:
            entities: List of parsed entities
            entity_type: Type of entity
            
        Returns:
            Path to saved file
        """
        output_path = get_parsed_file_path(entity_type)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for entity in entities:
                json_line = json.dumps(entity, ensure_ascii=False)
                f.write(json_line + "\n")
        
        logger.info(f"Saved {len(entities)} {entity_type}s to {output_path}")
        return output_path
    
    def parse_all(self) -> Dict[str, int]:
        """
        Parse all raw files and save to JSONL.
        
        Returns:
            Dictionary with counts per entity type
        """
        results = {}
        
        for entity_type in ENTITY_TYPES:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {entity_type}")
            logger.info(f"{'='*60}")
            
            self.reset_stats()
            
            entities = self.parse_all_by_type(entity_type)
            
            if entities:
                self.save_parsed_data(entities, entity_type)
            
            results[entity_type] = len(entities)
            
            # Log stats for this type
            logger.info(
                f"{entity_type}: {self.stats['success']}/{self.stats['total']} parsed "
                f"({self.stats['no_infobox']} no infobox, {self.stats['parse_error']} errors)"
            )
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict[str, int]) -> None:
        """Print parsing summary."""
        print("\n" + "=" * 60)
        print("PARSING SUMMARY")
        print("=" * 60)
        
        total = 0
        for entity_type, count in results.items():
            print(f"  {entity_type}: {count} entities")
            total += count
        
        print("-" * 60)
        print(f"  TOTAL: {total} entities parsed")
        print("=" * 60)


def main():
    """Main entry point for the parser CLI."""
    parser = argparse.ArgumentParser(
        description="Parse Wikipedia infoboxes for Vietnamese football data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Parse all entity types:
    python -m parser.infobox_parser --parse-all
    
  Parse only players:
    python -m parser.infobox_parser --entity-type player
    
  Parse a specific file:
    python -m parser.infobox_parser --file data/raw/player_12345.json
        """,
    )
    
    parser.add_argument(
        "--parse-all",
        action="store_true",
        help="Parse all raw files for all entity types",
    )
    parser.add_argument(
        "--entity-type",
        type=str,
        choices=ENTITY_TYPES,
        help="Parse only a specific entity type",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Parse a single raw JSON file",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.parse_all, args.entity_type, args.file]):
        parser.error("Must specify --parse-all, --entity-type, or --file")
    
    # Create parser
    infobox_parser = InfoboxParser()
    
    # Run parser
    if args.parse_all:
        infobox_parser.parse_all()
    elif args.entity_type:
        entities = infobox_parser.parse_all_by_type(args.entity_type)
        if entities:
            infobox_parser.save_parsed_data(entities, args.entity_type)
        print(f"\nParsed {len(entities)} {args.entity_type}s")
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        
        result = infobox_parser.parse_file(file_path)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("Failed to parse file (no infobox found or parse error)")


if __name__ == "__main__":
    main()
