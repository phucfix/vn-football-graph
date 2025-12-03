"""
Configuration settings for Vietnam Football Knowledge Graph pipeline.

This module contains all configurable parameters including:
- Neo4j Aura connection settings
- Wikipedia API settings and categories
- File paths for data storage
- Rate limiting settings
"""

import os
from pathlib import Path

# =============================================================================
# PROJECT PATHS
# =============================================================================

# Base directory (project root)
BASE_DIR = Path(__file__).parent.parent.absolute()

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PARSED_DATA_DIR = DATA_DIR / "parsed"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EDGES_DATA_DIR = DATA_DIR / "edges"

# Reports directory
REPORTS_DIR = BASE_DIR / "reports"

# Neo4j import directory
NEO4J_IMPORT_DIR = BASE_DIR / "neo4j_import"

# =============================================================================
# NEO4J AURA SETTINGS
# =============================================================================

# Neo4j Aura connection (use neo4j+s:// for Aura cloud)
NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j+s://xxxxxxxx.databases.neo4j.io")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")

# Connection pool settings for Aura
NEO4J_MAX_CONNECTION_LIFETIME = 3600  # 1 hour
NEO4J_MAX_CONNECTION_POOL_SIZE = 50
NEO4J_CONNECTION_TIMEOUT = 30  # seconds

# =============================================================================
# WIKIPEDIA API SETTINGS
# =============================================================================

# Vietnamese Wikipedia
WIKI_SITE = "vi.wikipedia.org"
WIKI_PATH = "/w/"
WIKI_USER_AGENT = "VietnamFootballKG/1.0 (https://github.com/example/vn-football-kg; contact@example.com)"

# Rate limiting (to be respectful to Wikipedia servers)
API_DELAY_SECONDS = 1.0  # Delay between API calls
API_MAX_RETRIES = 3  # Max retries on failure
API_RETRY_DELAY = 5  # Seconds to wait before retry

# =============================================================================
# WIKIPEDIA CATEGORIES TO CRAWL
# =============================================================================

# Categories mapping: category_name -> entity_type
WIKI_CATEGORIES = {
    # =========================================================================
    # PLAYERS (Male + Female + National Team)
    # =========================================================================
    "Cầu thủ bóng đá Việt Nam": "player",
    "Cầu thủ bóng đá nữ Việt Nam": "player",  # Women's football
    "Cầu thủ đội tuyển bóng đá quốc gia Việt Nam": "player",  # National team players
    "Quả bóng vàng Việt Nam": "player",  # Award winners (mostly players)
    
    # =========================================================================
    # COACHES
    # =========================================================================
    "Huấn luyện viên bóng đá Việt Nam": "coach",
    
    # =========================================================================
    # CLUBS (Male + Female)
    # =========================================================================
    "Câu lạc bộ bóng đá Việt Nam": "club",
    
    # =========================================================================
    # NATIONAL TEAMS (All levels)
    # =========================================================================
    "Đội tuyển bóng đá quốc gia Việt Nam": "national_team",
    "Đội tuyển bóng đá nữ quốc gia Việt Nam": "national_team",  # Women's national teams
    
    # =========================================================================
    # STADIUMS
    # =========================================================================
    "Địa điểm bóng đá Việt Nam": "stadium",
    
    # =========================================================================
    # COMPETITIONS & SEASONS
    # =========================================================================
    "Giải bóng đá Việt Nam": "competition",  # Main competitions
    "Giải đấu bóng đá tại Việt Nam": "competition",  # More competitions
    "Cúp bóng đá Việt Nam": "season",  # Cup seasons by year
    "Giải thưởng bóng đá Việt Nam": "award",  # Awards
}

# Additional sub-categories to crawl (optional, for more comprehensive data)
WIKI_SUBCATEGORIES = {
    # V-League seasons
    "Giải bóng đá vô địch quốc gia Việt Nam": "season",
    "Giải bóng đá hạng nhất quốc gia Việt Nam": "season",
}

# Maximum recursion depth for subcategories (0 = only direct members)
CATEGORY_RECURSION_DEPTH = 1

# =============================================================================
# ENTITY TYPE CONFIGURATIONS
# =============================================================================

ENTITY_TYPES = ["player", "coach", "club", "national_team", "stadium", "competition", "season", "award"]

# File naming patterns
RAW_FILE_PATTERN = "{entity_type}_{page_id}.json"
PARSED_FILE_PATTERN = "{entity_type}s.jsonl"
PROCESSED_FILE_PATTERN = "{entity_type}s_clean.csv"

# =============================================================================
# INFOBOX TEMPLATES (English field names)
# =============================================================================

# Common infobox template names used in Vietnamese Wikipedia
INFOBOX_TEMPLATES = {
    "player": [
        "Infobox football biography",
        "Infobox footballer",
        "Thông tin cầu thủ bóng đá",
        "Thông tin tiểu sử bóng đá",
    ],
    "coach": [
        "Infobox football biography",
        "Infobox football official",
        "Thông tin huấn luyện viên bóng đá",
    ],
    "club": [
        "Infobox football club",
        "Thông tin câu lạc bộ bóng đá",
    ],
    "national_team": [
        "Infobox national football team",
        "Thông tin đội tuyển bóng đá quốc gia",
    ],
    "stadium": [
        "Infobox stadium",
        "Infobox venue",
        "Thông tin sân vận động",
        "Thông tin địa điểm thể thao",
    ],
    "competition": [
        "Infobox football league",
        "Infobox football tournament",
        "Thông tin giải bóng đá",
    ],
    "season": [
        "Infobox football league season",
        "Infobox football tournament season",
        "Thông tin mùa giải bóng đá",
    ],
    "award": [
        "Infobox award",
        "Thông tin giải thưởng",
    ],
}

# =============================================================================
# FIELD MAPPINGS (Vietnamese -> English)
# =============================================================================

# Maps Vietnamese infobox field names to standardized English names
FIELD_MAPPINGS = {
    # Common fields
    "tên": "name",
    "tên đầy đủ": "full_name",
    "tên_đầy_đủ": "full_name",
    "ngày sinh": "date_of_birth",
    "ngày_sinh": "date_of_birth",
    "nơi sinh": "place_of_birth",
    "nơi_sinh": "place_of_birth",
    
    # Player fields
    "vị trí": "position",
    "vị_trí": "position",
    "chiều cao": "height",
    "chiều_cao": "height",
    "cân nặng": "weight",
    "cân_nặng": "weight",
    "chân thuận": "preferred_foot",
    "chân_thuận": "preferred_foot",
    "số áo": "shirt_number",
    "số_áo": "shirt_number",
    
    # Career fields
    "câu lạc bộ hiện tại": "current_club",
    "câu_lạc_bộ_hiện_tại": "current_club",
    "năm hoạt động": "years_active",
    "năm_hoạt_động": "years_active",
    
    # Club fields
    "thành lập": "founded",
    "sân vận động": "stadium",
    "sân_vận_động": "stadium",
    "sức chứa": "capacity",
    "sức_chứa": "capacity",
    "chủ tịch": "chairman",
    "chủ_tịch": "chairman",
    "huấn luyện viên": "manager",
    "huấn_luyện_viên": "manager",
    "giải đấu": "league",
    "giải_đấu": "league",
    
    # Stadium fields
    "địa điểm": "location",
    "địa_điểm": "location",
    "chủ sở hữu": "owner",
    "chủ_sở_hữu": "owner",
    "sức chứa tối đa": "max_capacity",
    "sức_chứa_tối_đa": "max_capacity",
    "kích thước sân": "field_size",
    "kích_thước_sân": "field_size",
    "mặt sân": "surface",
    "mặt_sân": "surface",
    "năm xây dựng": "year_built",
    "năm_xây_dựng": "year_built",
    "khai trương": "opened",
    
    # Competition fields
    "quốc gia": "country",
    "quốc_gia": "country",
    "số đội": "teams",
    "số_đội": "teams",
    "cấp độ": "level",
    "cấp_độ": "level",
    "hệ thống": "system",
    "hệ_thống": "system",
    "vô địch hiện tại": "current_champion",
    "vô_địch_hiện_tại": "current_champion",
    "đội vô địch nhiều nhất": "most_titles",
    "đội_vô_địch_nhiều_nhất": "most_titles",
    
    # Season fields  
    "mùa giải": "season_name",
    "mùa_giải": "season_name",
    "vô địch": "champion",
    "á quân": "runner_up",
    "á_quân": "runner_up",
    "hạng ba": "third_place",
    "hạng_ba": "third_place",
    "vua phá lưới": "top_scorer",
    "vua_phá_lưới": "top_scorer",
    "cầu thủ xuất sắc": "best_player",
    "cầu_thủ_xuất_sắc": "best_player",
    
    # Award fields
    "người chiến thắng": "winner",
    "người_chiến_thắng": "winner",
    "năm": "year",
}

# =============================================================================
# POSITION STANDARDIZATION
# =============================================================================

# Maps various position names to standardized codes
POSITION_MAPPINGS = {
    # Goalkeepers
    "thủ môn": "GK",
    "goalkeeper": "GK",
    "gk": "GK",
    
    # Defenders
    "hậu vệ": "DF",
    "hậu vệ trung tâm": "CB",
    "hậu vệ phải": "RB",
    "hậu vệ trái": "LB",
    "hậu vệ cánh": "FB",
    "trung vệ": "CB",
    "defender": "DF",
    "centre-back": "CB",
    "center-back": "CB",
    "right-back": "RB",
    "left-back": "LB",
    "full-back": "FB",
    
    # Midfielders
    "tiền vệ": "MF",
    "tiền vệ trung tâm": "CM",
    "tiền vệ phòng ngự": "DM",
    "tiền vệ tấn công": "AM",
    "tiền vệ cánh": "WM",
    "tiền vệ phải": "RM",
    "tiền vệ trái": "LM",
    "midfielder": "MF",
    "central midfielder": "CM",
    "defensive midfielder": "DM",
    "attacking midfielder": "AM",
    "winger": "WM",
    "right midfielder": "RM",
    "left midfielder": "LM",
    
    # Forwards
    "tiền đạo": "FW",
    "tiền đạo cắm": "ST",
    "tiền đạo cánh": "WF",
    "forward": "FW",
    "striker": "ST",
    "centre-forward": "CF",
    "center-forward": "CF",
}

# =============================================================================
# DATA PROCESSING SETTINGS
# =============================================================================

# Minimum required fields for valid entities
REQUIRED_FIELDS = {
    "player": ["name", "wiki_id"],
    "coach": ["name", "wiki_id"],
    "club": ["name", "wiki_id"],
    "national_team": ["name", "wiki_id"],
    "stadium": ["name", "wiki_id"],
    "competition": ["name", "wiki_id"],
    "season": ["name", "wiki_id"],
    "award": ["name", "wiki_id"],
}

# Fields to use for deduplication
DEDUP_FIELDS = {
    "player": ["name", "date_of_birth"],
    "coach": ["name"],
    "club": ["name"],
    "national_team": ["name"],
    "stadium": ["name"],
    "competition": ["name"],
    "season": ["name"],
    "award": ["name"],
}

# =============================================================================
# LOGGING SETTINGS
# =============================================================================

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "logs" / "pipeline.log"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        RAW_DATA_DIR,
        PARSED_DATA_DIR,
        PROCESSED_DATA_DIR,
        EDGES_DATA_DIR,
        REPORTS_DIR,
        LOG_FILE.parent,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_raw_file_path(entity_type: str, page_id: int) -> Path:
    """Get the path for a raw JSON file."""
    filename = RAW_FILE_PATTERN.format(entity_type=entity_type, page_id=page_id)
    return RAW_DATA_DIR / filename


def get_parsed_file_path(entity_type: str) -> Path:
    """Get the path for a parsed JSONL file."""
    filename = PARSED_FILE_PATTERN.format(entity_type=entity_type)
    return PARSED_DATA_DIR / filename


def get_processed_file_path(entity_type: str) -> Path:
    """Get the path for a processed CSV file."""
    filename = PROCESSED_FILE_PATTERN.format(entity_type=entity_type)
    return PROCESSED_DATA_DIR / filename


def get_edge_file_path(edge_type: str) -> Path:
    """Get the path for an edge CSV file."""
    return EDGES_DATA_DIR / f"{edge_type}.csv"


# Initialize directories on import
ensure_directories()
