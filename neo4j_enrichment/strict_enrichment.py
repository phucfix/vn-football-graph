"""
Strict Enrichment Strategy for Vietnam Football Knowledge Graph

Yêu cầu bài tập:
1. Làm giàu dữ liệu đồ thị bằng phân tích dữ liệu văn bản
2. Mô hình nhận dạng thực thể (node) liên quan chủ đề
3. Mô hình nhận dạng mối quan hệ (cạnh) giữa các thực thể

Nguyên tắc STRICT:
- CHỈ entities Việt Nam hoặc liên quan trực tiếp đến bóng đá Việt Nam
- CHỈ accept entities từ dictionary match (đã có trong DB)
- NEW entities phải qua human review trước khi import
- Relations CHỈ giữa các entities đã tồn tại trong DB
"""

import json
import re
import csv
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
ENRICHMENT_DIR = DATA_DIR / "enrichment"


@dataclass
class StrictEnrichmentConfig:
    """Configuration for strict enrichment."""
    
    # Only Vietnamese entities
    require_vietnam_context: bool = True
    
    # Entity validation - SUPER STRICT
    min_confidence_dictionary: float = 0.95  # Dictionary matches
    min_confidence_model: float = 1.0        # Disable model predictions for new entities
    min_entity_length: int = 4               # Minimum 4 chars
    
    # ONLY accept dictionary source for new entities
    only_dictionary_for_new: bool = True
    
    # Relation validation  
    require_both_entities_exist: bool = True  # Both subject and object must be in DB
    min_relation_confidence: float = 0.85
    
    # Human review
    export_candidates_for_review: bool = True
    auto_import_threshold: float = 1.0  # Only 100% confident = auto import
    
    # Allowed entity types for enrichment
    allowed_entity_types: Set[str] = field(default_factory=lambda: {
        "PLAYER",      # Cầu thủ
        "COACH",       # HLV
        "CLUB",        # Câu lạc bộ
        "COMPETITION", # Giải đấu
        "STADIUM",     # Sân vận động
        "NATIONAL_TEAM", # Đội tuyển
    })
    
    # Blocked entity types (will NOT create as nodes)
    blocked_entity_types: Set[str] = field(default_factory=lambda: {
        "DATE",        # Ngày tháng -> không cần node
        "POSITION",    # Vị trí -> là property của Player
        "PROVINCE",    # Tỉnh -> đã có đủ trong DB
        "EVENT",       # Sự kiện chung
        "ORGANIZATION", # Tổ chức (VFF, FIFA...)
        "UNKNOWN",     # Unknown type
    })
    
    # Blacklist patterns for entity text
    entity_text_blacklist: Set[str] = field(default_factory=lambda: {
        "vff", "fifa", "afc", "aff",  # Organizations
        "báo", "tạp chí", "newspaper",  # Media
        "học viện", "academy",  # Academies
        "công ty", "company",  # Companies
        "liên đoàn", "federation",  # Federations
        "hiệp hội", "association",  # Associations
    })


class VietnamEntityValidator:
    """Validate entities are related to Vietnamese football."""
    
    # Vietnamese football indicators
    VN_INDICATORS = {
        # Địa danh Việt Nam
        "việt nam", "vietnam", "hà nội", "sài gòn", "đà nẵng", "hải phòng",
        "thành phố hồ chí minh", "tp.hcm", "tphcm",
        
        # Giải đấu VN
        "v.league", "v-league", "hạng nhất", "hạng nhì", "cúp quốc gia",
        "siêu cúp", "aff cup", "sea games", "asean",
        
        # Đội tuyển
        "đội tuyển", "u-23", "u23", "u-22", "u22", "u-21", "u21", "u-19", "u19",
        
        # CLB VN patterns
        "fc", "clb", "câu lạc bộ",
    }
    
    # Known Vietnamese clubs (subset)
    VN_CLUBS = {
        "hà nội", "hoàng anh gia lai", "hagl", "bình dương", "becamex",
        "viettel", "công an hà nội", "slna", "sông lam nghệ an",
        "đà nẵng", "shb đà nẵng", "hải phòng", "thanh hóa", "nam định",
        "quảng ninh", "tp.hcm", "sài gòn", "bình định", "khánh hòa",
    }
    
    @classmethod
    def is_vietnam_related(cls, text: str, context: str = "") -> bool:
        """Check if entity is related to Vietnamese football."""
        text_lower = text.lower()
        context_lower = context.lower()
        
        # Check text itself
        for indicator in cls.VN_INDICATORS:
            if indicator in text_lower:
                return True
        
        # Check context
        for indicator in cls.VN_INDICATORS:
            if indicator in context_lower:
                return True
        
        # Check if it's a known VN club
        for club in cls.VN_CLUBS:
            if club in text_lower:
                return True
        
        return False
    
    @classmethod
    def is_foreign_entity(cls, text: str) -> bool:
        """Check if entity is clearly foreign (should be excluded)."""
        text_lower = text.lower()
        
        # Foreign league indicators
        foreign_indicators = [
            "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
            "champions league", "europa league", "world cup",
            "manchester", "liverpool", "chelsea", "arsenal", "barcelona",
            "real madrid", "bayern", "juventus", "psg", "inter", "milan",
            "brazil", "argentina", "england", "spain", "germany", "france",
            "italy", "portugal", "netherlands", "belgium",
        ]
        
        for indicator in foreign_indicators:
            if indicator in text_lower:
                return True
        
        return False


class ExistingEntityMatcher:
    """Match entities against existing database."""
    
    def __init__(self):
        self.players: Dict[str, dict] = {}
        self.coaches: Dict[str, dict] = {}
        self.clubs: Dict[str, dict] = {}
        self.competitions: Dict[str, dict] = {}
        self.stadiums: Dict[str, dict] = {}
        self.national_teams: Dict[str, dict] = {}  # Added
        self.provinces: Dict[str, dict] = {}
        
        self._load_existing_entities()
    
    def _load_existing_entities(self):
        """Load all existing entities from CSV files."""
        # Load players
        if (PROCESSED_DIR / "players_clean.csv").exists():
            with open(PROCESSED_DIR / "players_clean.csv", encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    wiki_id = row.get('wiki_id')
                    name = row.get('name', '').strip()
                    canonical = row.get('canonical_name', '').strip()
                    
                    if name:
                        self.players[name.lower()] = row
                    if canonical and canonical != name:
                        self.players[canonical.lower()] = row
                    if wiki_id:
                        self.players[f"wiki:{wiki_id}"] = row
        
        # Load clubs
        if (PROCESSED_DIR / "clubs_clean.csv").exists():
            with open(PROCESSED_DIR / "clubs_clean.csv", encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    wiki_id = row.get('wiki_id')
                    name = row.get('name', '').strip()
                    
                    if name:
                        self.clubs[name.lower()] = row
                        # Also add without "FC", "CLB" prefix
                        clean_name = re.sub(r'^(fc|clb|câu lạc bộ)\s+', '', name.lower())
                        self.clubs[clean_name] = row
                    if wiki_id:
                        self.clubs[f"wiki:{wiki_id}"] = row
        
        # Load competitions
        if (PROCESSED_DIR / "competitions_clean.csv").exists():
            with open(PROCESSED_DIR / "competitions_clean.csv", encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    wiki_id = row.get('wiki_id')
                    name = row.get('name', '').strip()
                    
                    if name:
                        self.competitions[name.lower()] = row
                    if wiki_id:
                        self.competitions[f"wiki:{wiki_id}"] = row
        
        # Load coaches
        if (PROCESSED_DIR / "coaches_clean.csv").exists():
            with open(PROCESSED_DIR / "coaches_clean.csv", encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    wiki_id = row.get('wiki_id')
                    name = row.get('name', '').strip()
                    
                    if name:
                        self.coaches[name.lower()] = row
                    if wiki_id:
                        self.coaches[f"wiki:{wiki_id}"] = row
        
        # Load stadiums
        if (PROCESSED_DIR / "stadiums_clean.csv").exists():
            with open(PROCESSED_DIR / "stadiums_clean.csv", encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    wiki_id = row.get('wiki_id')
                    name = row.get('name', '').strip()
                    
                    if name:
                        self.stadiums[name.lower()] = row
                    if wiki_id:
                        self.stadiums[f"wiki:{wiki_id}"] = row
        
        # Load national teams
        if (PROCESSED_DIR / "national_teams_clean.csv").exists():
            with open(PROCESSED_DIR / "national_teams_clean.csv", encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    wiki_id = row.get('wiki_id')
                    name = row.get('name', '').strip()
                    canonical = row.get('canonical_name', '').strip()
                    
                    if name:
                        self.national_teams[name.lower()] = row
                    if canonical and canonical != name:
                        self.national_teams[canonical.lower()] = row
                        # Also add short form
                        short = canonical.replace('Đội tuyển ', '').lower()
                        self.national_teams[short] = row
                    if wiki_id:
                        self.national_teams[f"wiki:{wiki_id}"] = row
        
        # Load provinces
        if (PROCESSED_DIR / "provinces_reference.csv").exists():
            with open(PROCESSED_DIR / "provinces_reference.csv", encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    name = row.get('name', '').strip()
                    if name:
                        self.provinces[name.lower()] = row
        
        print(f"Loaded existing entities:")
        print(f"  Players: {len(self.players)}")
        print(f"  Coaches: {len(self.coaches)}")
        print(f"  Clubs: {len(self.clubs)}")
        print(f"  Competitions: {len(self.competitions)}")
        print(f"  Stadiums: {len(self.stadiums)}")
        print(f"  National Teams: {len(self.national_teams)}")
        print(f"  Provinces: {len(self.provinces)}")
    
    def find_match(self, text: str, entity_type: str) -> Optional[dict]:
        """Find matching existing entity."""
        text_lower = text.lower().strip()
        
        # Try exact match first
        if entity_type == "PLAYER":
            if text_lower in self.players:
                return self.players[text_lower]
        elif entity_type == "COACH":
            if text_lower in self.coaches:
                return self.coaches[text_lower]
        elif entity_type == "CLUB":
            if text_lower in self.clubs:
                return self.clubs[text_lower]
        elif entity_type == "COMPETITION":
            if text_lower in self.competitions:
                return self.competitions[text_lower]
        elif entity_type == "STADIUM":
            if text_lower in self.stadiums:
                return self.stadiums[text_lower]
        elif entity_type == "NATIONAL_TEAM":
            if text_lower in self.national_teams:
                return self.national_teams[text_lower]
        elif entity_type == "PROVINCE":
            if text_lower in self.provinces:
                return self.provinces[text_lower]
        
        return None
    
    def entity_exists(self, text: str, entity_type: str) -> bool:
        """Check if entity exists in database."""
        return self.find_match(text, entity_type) is not None


@dataclass
class ValidatedEntity:
    """An entity that passed strict validation."""
    text: str
    entity_type: str
    wiki_id: Optional[int]
    confidence: float
    source: str  # 'dictionary', 'model', 'pattern'
    matched_existing: Optional[dict]
    is_new: bool
    vietnam_related: bool
    validation_notes: List[str] = field(default_factory=list)


@dataclass  
class ValidatedRelation:
    """A relation that passed strict validation."""
    subject: ValidatedEntity
    predicate: str
    object: ValidatedEntity
    confidence: float
    context: str
    source: str
    validation_notes: List[str] = field(default_factory=list)


class StrictEnrichmentValidator:
    """Validate entities and relations with strict rules."""
    
    def __init__(self, config: StrictEnrichmentConfig = None):
        self.config = config or StrictEnrichmentConfig()
        self.entity_matcher = ExistingEntityMatcher()
        self.stats = defaultdict(int)
    
    def validate_entity(self, entity: dict, context: str = "") -> Optional[ValidatedEntity]:
        """
        Validate an entity with strict rules.
        
        Returns ValidatedEntity if valid, None if should be rejected.
        """
        text = entity.get("text", "").strip()
        entity_type = entity.get("type", "")
        confidence = entity.get("confidence", 0.0)
        source = entity.get("source", "unknown")
        wiki_id = entity.get("wiki_id")
        
        notes = []
        
        # Rule 1: Check entity type is allowed
        if entity_type in self.config.blocked_entity_types:
            self.stats["blocked_type"] += 1
            return None
        
        if entity_type not in self.config.allowed_entity_types:
            self.stats["unknown_type"] += 1
            return None
        
        # Rule 2: Check minimum length
        if len(text) < self.config.min_entity_length:
            self.stats["too_short"] += 1
            return None
        
        # Rule 3: Check confidence by source
        if source == "dictionary":
            if confidence < self.config.min_confidence_dictionary:
                self.stats["low_confidence"] += 1
                return None
        else:
            if confidence < self.config.min_confidence_model:
                self.stats["low_confidence_model"] += 1
                return None
        
        # Rule 4: Check blacklist patterns
        text_lower = text.lower()
        for blacklist_term in self.config.entity_text_blacklist:
            if blacklist_term in text_lower:
                self.stats["blacklisted"] += 1
                return None
        
        # Rule 5: Check if foreign entity (reject)
        if VietnamEntityValidator.is_foreign_entity(text):
            self.stats["foreign_entity"] += 1
            return None
        
        # Rule 6: Check Vietnam relation
        vietnam_related = VietnamEntityValidator.is_vietnam_related(text, context)
        if self.config.require_vietnam_context and not vietnam_related:
            # For new entities, must be Vietnam related
            existing = self.entity_matcher.find_match(text, entity_type)
            if existing is None:
                self.stats["not_vietnam_related"] += 1
                return None
        
        # Rule 7: Check if exists in database
        existing_match = self.entity_matcher.find_match(text, entity_type)
        is_new = existing_match is None
        
        # Rule 8: For NEW entities, ONLY accept dictionary source
        if is_new and self.config.only_dictionary_for_new:
            if source != "dictionary":
                self.stats["new_not_dictionary"] += 1
                return None
        
        if is_new:
            notes.append("NEW: Requires human review")
            self.stats["new_candidate"] += 1
        else:
            notes.append(f"EXISTING: Matched {existing_match.get('name', existing_match.get('wiki_id'))}")
            self.stats["matched_existing"] += 1
        
        return ValidatedEntity(
            text=text,
            entity_type=entity_type,
            wiki_id=wiki_id,
            confidence=confidence,
            source=source,
            matched_existing=existing_match,
            is_new=is_new,
            vietnam_related=vietnam_related,
            validation_notes=notes,
        )
    
    def validate_relation(
        self,
        subject: dict,
        predicate: str,
        obj: dict,
        confidence: float,
        context: str,
        source: str,
    ) -> Optional[ValidatedRelation]:
        """
        Validate a relation with strict rules.
        
        Only accepts relations where BOTH entities exist in database.
        """
        # Validate subject
        subj_validated = self.validate_entity(subject, context)
        if subj_validated is None:
            self.stats["relation_invalid_subject"] += 1
            return None
        
        # Validate object
        obj_validated = self.validate_entity(obj, context)
        if obj_validated is None:
            self.stats["relation_invalid_object"] += 1
            return None
        
        # Rule: Both must exist in database
        if self.config.require_both_entities_exist:
            if subj_validated.is_new or obj_validated.is_new:
                self.stats["relation_entity_not_exist"] += 1
                return None
        
        # Rule: Minimum confidence
        if confidence < self.config.min_relation_confidence:
            self.stats["relation_low_confidence"] += 1
            return None
        
        notes = [
            f"Subject: {subj_validated.text} ({subj_validated.entity_type})",
            f"Object: {obj_validated.text} ({obj_validated.entity_type})",
        ]
        
        self.stats["valid_relation"] += 1
        
        return ValidatedRelation(
            subject=subj_validated,
            predicate=predicate,
            object=obj_validated,
            confidence=confidence,
            context=context,
            source=source,
            validation_notes=notes,
        )
    
    def get_stats(self) -> dict:
        """Get validation statistics."""
        return dict(self.stats)


def main():
    """Test the strict enrichment validator."""
    print("=== Strict Enrichment Validator Test ===\n")
    
    validator = StrictEnrichmentValidator()
    
    # Test entities
    test_entities = [
        {"text": "Nguyễn Quang Hải", "type": "PLAYER", "confidence": 1.0, "source": "dictionary"},
        {"text": "Manchester United", "type": "CLUB", "confidence": 0.95, "source": "model"},
        {"text": "V.League 2024", "type": "COMPETITION", "confidence": 0.9, "source": "pattern"},
        {"text": "tiền đạo", "type": "POSITION", "confidence": 0.95, "source": "pattern"},
        {"text": "Hà Nội FC", "type": "CLUB", "confidence": 1.0, "source": "dictionary"},
    ]
    
    print("Testing entities:")
    for entity in test_entities:
        result = validator.validate_entity(entity, "Bóng đá Việt Nam")
        status = "✅ VALID" if result else "❌ REJECTED"
        print(f"  {status}: {entity['text']} ({entity['type']})")
        if result:
            print(f"      Notes: {result.validation_notes}")
    
    print(f"\nStats: {validator.get_stats()}")


if __name__ == "__main__":
    main()
