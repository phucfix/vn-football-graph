"""
Named Entity Recognizer for Vietnam Football Knowledge Graph Enrichment

This module provides Vietnamese football-specific Named Entity Recognition (NER)
using a hybrid approach:
1. Dictionary-based matching (existing entities from Neo4j)
2. PhoBERT-based NER for unknown entities
3. Rule-based patterns for dates, positions, etc.

Entity Types:
- PLAYER: Player names (e.g., "Nguyễn Công Phượng")
- COACH: Coach names (e.g., "Park Hang-seo")
- CLUB: Club names (e.g., "Sài Gòn FC", "HAGL")
- NATIONAL_TEAM: National teams (e.g., "đội tuyển Việt Nam", "U23 Việt Nam")
- STADIUM: Stadium names (e.g., "Mỹ Đình", "Thống Nhất")
- PROVINCE: Provinces (e.g., "Hà Nội", "TP.HCM")
- COMPETITION: Tournament/league names (e.g., "V.League", "AFF Cup")
- EVENT: Specific match/event (e.g., "chung kết AFF Cup 2008")
- DATE: Dates (e.g., "năm 2015", "tháng 1 năm 2024")
- POSITION: Player positions (e.g., "tiền đạo", "thủ môn")

Usage:
    python -m nlp.entity_recognizer --process-all
    python -m nlp.entity_recognizer --sentence "Công Phượng ghi bàn cho HAGL"
"""

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import BASE_DIR, DATA_DIR, PROCESSED_DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

ENRICHMENT_DIR = DATA_DIR / "enrichment"
PROCESSED_TEXTS_DIR = DATA_DIR / "processed_texts"
MODEL_CACHE_DIR = BASE_DIR / "nlp" / "models"

# Entity types
ENTITY_TYPES = [
    "PLAYER", "COACH", "CLUB", "NATIONAL_TEAM", "STADIUM",
    "PROVINCE", "COMPETITION", "EVENT", "DATE", "POSITION"
]

# Vietnamese date patterns
DATE_PATTERNS = [
    r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',  # ngày 15 tháng 12 năm 2024
    r'tháng\s+(\d{1,2})\s+năm\s+(\d{4})',  # tháng 12 năm 2024
    r'năm\s+(\d{4})',  # năm 2024
    r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # 15/12/2024 or 15-12-2024
    r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # 2024/12/15 or 2024-12-15
]

# Vietnamese position keywords
POSITION_KEYWORDS = {
    "thủ môn": "Goalkeeper",
    "hậu vệ": "Defender",
    "hậu vệ trái": "Left Back",
    "hậu vệ phải": "Right Back",
    "trung vệ": "Center Back",
    "tiền vệ": "Midfielder",
    "tiền vệ trung tâm": "Central Midfielder",
    "tiền vệ phòng ngự": "Defensive Midfielder",
    "tiền vệ tấn công": "Attacking Midfielder",
    "tiền vệ cánh": "Winger",
    "tiền đạo": "Forward",
    "tiền đạo cắm": "Striker",
    "tiền đạo lùi": "Second Striker",
}

# Competition name patterns
COMPETITION_PATTERNS = [
    r'V\.?\s*League\s*\d*',
    r'Hạng\s+nhất\s+quốc\s+gia',
    r'Cúp\s+quốc\s+gia',
    r'AFF\s+Cup\s*\d*',
    r'AFC\s+Cup\s*\d*',
    r'SEA\s+Games\s*\d*',
    r'Asian\s+Cup\s*\d*',
    r'World\s+Cup\s*\d*',
    r'Tiger\s+Cup\s*\d*',
    r'Suzuki\s+Cup\s*\d*',
    r'Mitsubishi\s+Electric\s+Cup\s*\d*',
]

# National team patterns
NATIONAL_TEAM_PATTERNS = [
    r'đội\s+tuyển\s+(?:bóng\s+đá\s+)?(?:quốc\s+gia\s+)?([A-Za-zÀ-ỹ\s]+)',
    r'ĐT\s*([A-Za-zÀ-ỹ]+)',
    r'ĐTVN',
    r'U\d{2}\s+([A-Za-zÀ-ỹ]+)',
    r'tuyển\s+([A-Za-zÀ-ỹ]+)',
]


@dataclass
class Entity:
    """Represents a recognized entity."""
    text: str
    entity_type: str
    start_pos: int
    end_pos: int
    confidence: float
    wiki_id: Optional[int] = None
    matched_name: Optional[str] = None  # Name in knowledge graph
    source: str = "unknown"  # "dictionary", "model", "pattern"
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "type": self.entity_type,
            "start": self.start_pos,
            "end": self.end_pos,
            "confidence": float(self.confidence) if self.confidence is not None else None,
            "wiki_id": int(self.wiki_id) if self.wiki_id is not None else None,
            "matched_name": self.matched_name,
            "source": self.source,
            "metadata": self.metadata,
        }


class EntityDictionary:
    """
    Dictionary-based entity matching using existing knowledge graph entities.
    
    Loads entity names from processed CSV files and provides fast lookup
    with fuzzy matching support.
    """
    
    def __init__(self, fuzzy_threshold: float = 0.85):
        """
        Initialize the entity dictionary.
        
        Args:
            fuzzy_threshold: Minimum similarity for fuzzy matching
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.entities: Dict[str, List[Dict]] = {}  # entity_type -> list of entities
        self.name_to_entity: Dict[str, Dict] = {}  # normalized_name -> entity info
        self.aliases: Dict[str, str] = {}  # alias -> canonical name
        
        self._load_entities()
        self._build_aliases()
    
    def _load_entities(self) -> None:
        """Load entities from processed CSV files."""
        import pandas as pd
        
        entity_files = {
            "PLAYER": PROCESSED_DATA_DIR / "players_clean.csv",
            "COACH": PROCESSED_DATA_DIR / "coaches_clean.csv",
            "CLUB": PROCESSED_DATA_DIR / "clubs_clean.csv",
            "NATIONAL_TEAM": PROCESSED_DATA_DIR / "national_teams_clean.csv",
            "STADIUM": PROCESSED_DATA_DIR / "stadiums_clean.csv",
            "COMPETITION": PROCESSED_DATA_DIR / "competitions_clean.csv",
            "PROVINCE": PROCESSED_DATA_DIR / "provinces_reference.csv",
            "POSITION": PROCESSED_DATA_DIR / "positions_reference.csv",
        }
        
        for entity_type, file_path in entity_files.items():
            if not file_path.exists():
                logger.warning(f"Entity file not found: {file_path}")
                continue
            
            try:
                df = pd.read_csv(file_path)
                self.entities[entity_type] = []
                
                # Determine name column
                name_col = None
                for col in ["name", "full_name", "club_name", "stadium_name", "province", "position"]:
                    if col in df.columns:
                        name_col = col
                        break
                
                if name_col is None:
                    logger.warning(f"No name column found in {file_path}")
                    continue
                
                # Load entities
                for _, row in df.iterrows():
                    name = str(row[name_col]).strip()
                    if not name or name == "nan":
                        continue
                    
                    wiki_id = row.get("wiki_id", row.get("page_id", None))
                    if pd.isna(wiki_id):
                        wiki_id = None
                    else:
                        wiki_id = int(wiki_id)
                    
                    entity_info = {
                        "name": name,
                        "wiki_id": wiki_id,
                        "entity_type": entity_type,
                    }
                    
                    self.entities[entity_type].append(entity_info)
                    
                    # Index by normalized name
                    norm_name = self._normalize_name(name)
                    self.name_to_entity[norm_name] = entity_info
                
                logger.info(f"Loaded {len(self.entities[entity_type])} {entity_type} entities")
                
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for matching."""
        # Lowercase
        name = name.lower()
        # Remove extra whitespace
        name = ' '.join(name.split())
        # Remove common suffixes/prefixes
        name = re.sub(r'\s*(fc|clb|câu lạc bộ|đội|sân|stadium)\s*', ' ', name)
        name = name.strip()
        return name
    
    def _build_aliases(self) -> None:
        """Build alias mappings for common abbreviations."""
        # Common Vietnamese football abbreviations
        abbreviations = {
            # Clubs
            "hagl": "hoàng anh gia lai",
            "slna": "sông lam nghệ an",
            "tphcm": "tp hồ chí minh",
            "tp.hcm": "tp hồ chí minh",
            "hn": "hà nội",
            "hnfc": "hà nội fc",
            "shb đà nẵng": "shb đà nẵng",
            "slfc": "sông lam nghệ an",
            "brvt": "bà rịa vũng tàu",
            
            # National teams
            "đtvn": "đội tuyển việt nam",
            "vn": "việt nam",
            
            # Common name shortcuts
            "công phượng": "nguyễn công phượng",
            "quang hải": "nguyễn quang hải",
            "văn toàn": "nguyễn văn toàn",
            "tiến linh": "nguyễn tiến linh",
            "xuân trường": "lương xuân trường",
        }
        
        for alias, canonical in abbreviations.items():
            norm_alias = self._normalize_name(alias)
            norm_canonical = self._normalize_name(canonical)
            if norm_canonical in self.name_to_entity:
                self.aliases[norm_alias] = norm_canonical
    
    def find_exact_match(self, text: str) -> Optional[Dict]:
        """
        Find exact match for text in dictionary.
        
        Args:
            text: Text to match
            
        Returns:
            Entity info dict or None
        """
        norm_text = self._normalize_name(text)
        
        # Check direct match
        if norm_text in self.name_to_entity:
            return self.name_to_entity[norm_text]
        
        # Check aliases
        if norm_text in self.aliases:
            canonical = self.aliases[norm_text]
            if canonical in self.name_to_entity:
                return self.name_to_entity[canonical]
        
        return None
    
    def find_fuzzy_match(
        self,
        text: str,
        entity_type: Optional[str] = None,
    ) -> Optional[Tuple[Dict, float]]:
        """
        Find fuzzy match for text in dictionary.
        
        Args:
            text: Text to match
            entity_type: Restrict to specific entity type
            
        Returns:
            Tuple of (entity info, similarity score) or None
        """
        try:
            from rapidfuzz import fuzz
        except ImportError:
            logger.warning("rapidfuzz not installed, fuzzy matching disabled")
            return None
        
        norm_text = self._normalize_name(text)
        best_match = None
        best_score = 0.0
        
        # Search in specific type or all types
        types_to_search = [entity_type] if entity_type else self.entities.keys()
        
        for etype in types_to_search:
            if etype not in self.entities:
                continue
            
            for entity_info in self.entities[etype]:
                norm_name = self._normalize_name(entity_info["name"])
                
                # Use token_set_ratio for better Vietnamese name matching
                score = fuzz.token_set_ratio(norm_text, norm_name) / 100.0
                
                if score > best_score and score >= self.fuzzy_threshold:
                    best_score = score
                    best_match = entity_info
        
        if best_match:
            return (best_match, best_score)
        
        return None
    
    def get_all_entity_names(self, entity_type: Optional[str] = None) -> Set[str]:
        """Get all entity names for pattern building."""
        names = set()
        
        types_to_get = [entity_type] if entity_type else self.entities.keys()
        
        for etype in types_to_get:
            if etype in self.entities:
                for entity_info in self.entities[etype]:
                    names.add(entity_info["name"])
        
        return names


class PatternMatcher:
    """
    Pattern-based entity recognition for specific entity types.
    
    Uses regex patterns for:
    - Dates
    - Positions
    - Competitions
    - National teams
    """
    
    def __init__(self):
        """Initialize pattern matchers."""
        self.date_patterns = [re.compile(p, re.IGNORECASE) for p in DATE_PATTERNS]
        self.competition_patterns = [re.compile(p, re.IGNORECASE) for p in COMPETITION_PATTERNS]
        self.national_team_patterns = [re.compile(p, re.IGNORECASE) for p in NATIONAL_TEAM_PATTERNS]
        self.position_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in POSITION_KEYWORDS.keys()) + r')\b',
            re.IGNORECASE
        )
    
    def find_dates(self, text: str) -> List[Entity]:
        """Find date entities in text."""
        entities = []
        
        for pattern in self.date_patterns:
            for match in pattern.finditer(text):
                entities.append(Entity(
                    text=match.group(0),
                    entity_type="DATE",
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,
                    source="pattern",
                ))
        
        return entities
    
    def find_positions(self, text: str) -> List[Entity]:
        """Find position entities in text."""
        entities = []
        
        for match in self.position_pattern.finditer(text):
            position_vn = match.group(0).lower()
            position_en = POSITION_KEYWORDS.get(position_vn, position_vn)
            
            entities.append(Entity(
                text=match.group(0),
                entity_type="POSITION",
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95,
                source="pattern",
                metadata={"english_name": position_en},
            ))
        
        return entities
    
    def find_competitions(self, text: str) -> List[Entity]:
        """Find competition entities in text."""
        entities = []
        
        for pattern in self.competition_patterns:
            for match in pattern.finditer(text):
                entities.append(Entity(
                    text=match.group(0),
                    entity_type="COMPETITION",
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.90,
                    source="pattern",
                ))
        
        return entities
    
    def find_national_teams(self, text: str) -> List[Entity]:
        """Find national team entities in text."""
        entities = []
        
        for pattern in self.national_team_patterns:
            for match in pattern.finditer(text):
                entities.append(Entity(
                    text=match.group(0),
                    entity_type="NATIONAL_TEAM",
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.85,
                    source="pattern",
                ))
        
        return entities
    
    def find_all(self, text: str) -> List[Entity]:
        """Find all pattern-based entities in text."""
        entities = []
        entities.extend(self.find_dates(text))
        entities.extend(self.find_positions(text))
        entities.extend(self.find_competitions(text))
        entities.extend(self.find_national_teams(text))
        return entities


class PhoBERTNER:
    """
    PhoBERT-based Named Entity Recognition for Vietnamese text.
    
    Uses pre-trained PhoBERT model with NER head for recognizing
    person names, organizations, and locations.
    """
    
    def __init__(
        self,
        model_name: str = "vinai/phobert-base",
        device: str = "auto",
        max_length: int = 256,
    ):
        """
        Initialize PhoBERT NER.
        
        Args:
            model_name: Hugging Face model name
            device: Device to use ("auto", "cuda", "cpu")
            max_length: Maximum sequence length
        """
        self.model_name = model_name
        self.max_length = max_length
        self.device = device
        
        self.model = None
        self.tokenizer = None
        self.ner_pipeline = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the model (lazy loading).
        
        Returns:
            True if successful
        """
        if self._initialized:
            return True
        
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
            
            # Determine device
            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"Loading PhoBERT model on {self.device}...")
            
            # Load tokenizer and model
            # Note: Using a general Vietnamese NER model or PhoBERT base
            # For better results, fine-tune on football-specific data
            
            # Try to use a Vietnamese NER model if available
            ner_model_name = "NlpHUST/ner-vietnamese-electra-base"
            
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(ner_model_name)
                self.model = AutoModelForTokenClassification.from_pretrained(ner_model_name)
            except Exception:
                # Fallback to general PhoBERT (won't have NER labels, but can be fine-tuned)
                logger.warning(f"Vietnamese NER model not available, using base PhoBERT")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                # For now, we'll rely on dictionary and pattern matching
                self._initialized = False
                return False
            
            # Create pipeline
            self.ner_pipeline = pipeline(
                "ner",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                aggregation_strategy="simple",
            )
            
            self._initialized = True
            logger.info("PhoBERT NER model loaded successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            logger.error("Install with: pip install transformers torch")
            return False
        except Exception as e:
            logger.error(f"Error initializing PhoBERT NER: {e}")
            return False
    
    def recognize(self, text: str) -> List[Entity]:
        """
        Recognize entities in text using PhoBERT.
        
        Args:
            text: Input text
            
        Returns:
            List of recognized entities
        """
        if not self._initialized:
            if not self.initialize():
                return []
        
        if self.ner_pipeline is None:
            return []
        
        try:
            # Run NER pipeline
            results = self.ner_pipeline(text[:self.max_length])
            
            entities = []
            for result in results:
                # Map NER labels to our entity types
                label = result.get("entity_group", result.get("entity", ""))
                
                entity_type = self._map_label_to_type(label)
                if entity_type is None:
                    continue
                
                entities.append(Entity(
                    text=result["word"],
                    entity_type=entity_type,
                    start_pos=result.get("start", 0),
                    end_pos=result.get("end", 0),
                    confidence=result.get("score", 0.5),
                    source="model",
                ))
            
            return entities
            
        except Exception as e:
            logger.error(f"Error in PhoBERT NER: {e}")
            return []
    
    def _map_label_to_type(self, label: str) -> Optional[str]:
        """Map NER label to our entity types."""
        label = label.upper()
        
        # Common NER label mappings
        mappings = {
            "PER": "PLAYER",  # Could be player or coach
            "PERSON": "PLAYER",
            "ORG": "CLUB",  # Could be club or organization
            "ORGANIZATION": "CLUB",
            "LOC": "PROVINCE",
            "LOCATION": "PROVINCE",
            "GPE": "PROVINCE",
            "DATE": "DATE",
            "TIME": "DATE",
            "EVENT": "EVENT",
        }
        
        return mappings.get(label)


class EntityRecognizer:
    """
    Main entity recognition class that combines multiple methods:
    1. Dictionary matching (highest priority for known entities)
    2. Pattern matching (for dates, positions, competitions)
    3. PhoBERT NER (for unknown entities)
    """
    
    def __init__(
        self,
        use_dictionary: bool = True,
        use_patterns: bool = True,
        use_model: bool = True,
        fuzzy_threshold: float = 0.85,
        model_device: str = "auto",
    ):
        """
        Initialize the entity recognizer.
        
        Args:
            use_dictionary: Enable dictionary-based matching
            use_patterns: Enable pattern-based matching
            use_model: Enable PhoBERT model
            fuzzy_threshold: Threshold for fuzzy matching
            model_device: Device for model ("auto", "cuda", "cpu")
        """
        self.use_dictionary = use_dictionary
        self.use_patterns = use_patterns
        self.use_model = use_model
        
        # Initialize components
        self.dictionary = EntityDictionary(fuzzy_threshold) if use_dictionary else None
        self.pattern_matcher = PatternMatcher() if use_patterns else None
        self.phobert_ner = PhoBERTNER(device=model_device) if use_model else None
        
        # Ensure output directory exists
        ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
    
    def recognize(
        self,
        text: str,
        use_fuzzy: bool = True,
    ) -> List[Entity]:
        """
        Recognize entities in text.
        
        Args:
            text: Input text
            use_fuzzy: Enable fuzzy dictionary matching
            
        Returns:
            List of recognized entities
        """
        entities = []
        used_spans: Set[Tuple[int, int]] = set()  # Track used character spans
        
        # 1. Pattern-based matching (highest confidence for specific types)
        if self.pattern_matcher:
            pattern_entities = self.pattern_matcher.find_all(text)
            for entity in pattern_entities:
                span = (entity.start_pos, entity.end_pos)
                if not self._spans_overlap(span, used_spans):
                    entities.append(entity)
                    used_spans.add(span)
        
        # 2. Dictionary matching
        if self.dictionary:
            dict_entities = self._dictionary_match(text, use_fuzzy)
            for entity in dict_entities:
                span = (entity.start_pos, entity.end_pos)
                if not self._spans_overlap(span, used_spans):
                    entities.append(entity)
                    used_spans.add(span)
        
        # 3. Model-based NER (for remaining text)
        if self.phobert_ner:
            model_entities = self.phobert_ner.recognize(text)
            for entity in model_entities:
                span = (entity.start_pos, entity.end_pos)
                if not self._spans_overlap(span, used_spans):
                    # Try to link to dictionary
                    if self.dictionary:
                        match = self.dictionary.find_fuzzy_match(entity.text, entity.entity_type)
                        if match:
                            entity_info, score = match
                            entity.wiki_id = entity_info.get("wiki_id")
                            entity.matched_name = entity_info.get("name")
                            entity.confidence = max(entity.confidence, score)
                    
                    entities.append(entity)
                    used_spans.add(span)
        
        # Sort by position
        entities.sort(key=lambda e: e.start_pos)
        
        return entities
    
    def _dictionary_match(self, text: str, use_fuzzy: bool = True) -> List[Entity]:
        """
        Find dictionary matches in text.
        
        Args:
            text: Input text
            use_fuzzy: Enable fuzzy matching
            
        Returns:
            List of entities found
        """
        entities = []
        
        if not self.dictionary:
            return entities
        
        # Get all entity names to search for
        for entity_type in self.dictionary.entities.keys():
            for entity_info in self.dictionary.entities[entity_type]:
                name = entity_info["name"]
                
                # Search for exact occurrences
                pattern = re.compile(re.escape(name), re.IGNORECASE)
                for match in pattern.finditer(text):
                    entities.append(Entity(
                        text=match.group(0),
                        entity_type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=1.0,  # Exact match
                        wiki_id=entity_info.get("wiki_id"),
                        matched_name=name,
                        source="dictionary",
                    ))
        
        return entities
    
    def _spans_overlap(
        self,
        span: Tuple[int, int],
        used_spans: Set[Tuple[int, int]],
    ) -> bool:
        """Check if a span overlaps with any used span."""
        start, end = span
        for used_start, used_end in used_spans:
            if start < used_end and end > used_start:
                return True
        return False
    
    def process_sentences(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
        max_sentences: int = -1,
    ) -> Dict[str, int]:
        """
        Process sentences file and recognize entities.
        
        Args:
            input_file: Input JSONL file with sentences
            output_file: Output JSONL file for results
            max_sentences: Maximum sentences to process (-1 for all)
            
        Returns:
            Statistics dict
        """
        stats = {
            "sentences_processed": 0,
            "entities_found": 0,
            "by_type": {},
            "by_source": {},
        }
        
        if output_file is None:
            output_file = ENRICHMENT_DIR / "recognized_entities.jsonl"
        
        # Count total lines for progress bar
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        if max_sentences > 0:
            total_lines = min(total_lines, max_sentences)
        
        with open(input_file, 'r', encoding='utf-8') as in_f, \
             open(output_file, 'w', encoding='utf-8') as out_f:
            
            for i, line in enumerate(tqdm(in_f, total=total_lines, desc="Processing")):
                if max_sentences > 0 and i >= max_sentences:
                    break
                
                try:
                    record = json.loads(line)
                    sentence = record.get("sentence", "")
                    
                    if not sentence:
                        continue
                    
                    # Recognize entities
                    entities = self.recognize(sentence)
                    
                    # Build output record
                    output_record = {
                        "sentence_id": record.get("sentence_id"),
                        "wiki_id": record.get("wiki_id"),
                        "entity_type": record.get("entity_type"),
                        "page_title": record.get("page_title"),
                        "sentence": sentence,
                        "entities": [e.to_dict() for e in entities],
                        "date_extracted": datetime.utcnow().isoformat(),
                    }
                    
                    out_f.write(json.dumps(output_record, ensure_ascii=False) + '\n')
                    
                    # Update stats
                    stats["sentences_processed"] += 1
                    stats["entities_found"] += len(entities)
                    
                    for entity in entities:
                        # By type
                        if entity.entity_type not in stats["by_type"]:
                            stats["by_type"][entity.entity_type] = 0
                        stats["by_type"][entity.entity_type] += 1
                        
                        # By source
                        if entity.source not in stats["by_source"]:
                            stats["by_source"][entity.source] = 0
                        stats["by_source"][entity.source] += 1
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at line {i}: {e}")
                except Exception as e:
                    logger.error(f"Error processing line {i}: {e}")
        
        logger.info(f"Processed {stats['sentences_processed']} sentences, found {stats['entities_found']} entities")
        
        return stats
    
    def recognize_single(self, text: str) -> Dict:
        """
        Recognize entities in a single text.
        
        Args:
            text: Input text
            
        Returns:
            Dict with entities
        """
        entities = self.recognize(text)
        
        return {
            "text": text,
            "entities": [e.to_dict() for e in entities],
            "date_extracted": datetime.utcnow().isoformat(),
        }


def main():
    """CLI entry point for entity recognizer."""
    parser = argparse.ArgumentParser(
        description="Named Entity Recognition for Vietnam Football KG"
    )
    
    parser.add_argument(
        "--process-all",
        action="store_true",
        help="Process all sentences from preprocessed texts",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input JSONL file with sentences",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSONL file for results",
    )
    parser.add_argument(
        "--sentence",
        type=str,
        help="Process a single sentence",
    )
    parser.add_argument(
        "--max-sentences",
        type=int,
        default=-1,
        help="Maximum sentences to process",
    )
    parser.add_argument(
        "--no-model",
        action="store_true",
        help="Disable PhoBERT model (dictionary + patterns only)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Device for model inference",
    )
    
    args = parser.parse_args()
    
    # Initialize recognizer
    recognizer = EntityRecognizer(
        use_model=not args.no_model,
        model_device=args.device,
    )
    
    if args.sentence:
        print(f"\n=== Processing Single Sentence ===")
        print(f"Input: {args.sentence}\n")
        
        result = recognizer.recognize_single(args.sentence)
        
        print("Entities found:")
        for entity in result["entities"]:
            wiki_str = f" (wiki_id={entity['wiki_id']})" if entity.get("wiki_id") else ""
            print(f"  [{entity['type']}] \"{entity['text']}\" "
                  f"(conf={entity['confidence']:.2f}, source={entity['source']}){wiki_str}")
        return
    
    if args.process_all:
        # Find input file
        input_file = Path(args.input) if args.input else None
        if input_file is None:
            # Find the most recent sentences file
            sentence_files = list(PROCESSED_TEXTS_DIR.glob("*_sentences.jsonl"))
            if not sentence_files:
                print("No sentence files found. Run text_preprocessor first.")
                return
            input_file = sentence_files[0]
        
        output_file = Path(args.output) if args.output else None
        
        print(f"\n=== Processing Sentences ===")
        print(f"Input: {input_file}")
        print(f"Output: {output_file or ENRICHMENT_DIR / 'recognized_entities.jsonl'}")
        
        stats = recognizer.process_sentences(
            input_file=input_file,
            output_file=output_file,
            max_sentences=args.max_sentences,
        )
        
        print(f"\nResults:")
        print(f"  Sentences processed: {stats['sentences_processed']}")
        print(f"  Entities found: {stats['entities_found']}")
        print(f"\n  By type:")
        for etype, count in sorted(stats["by_type"].items()):
            print(f"    {etype}: {count}")
        print(f"\n  By source:")
        for source, count in sorted(stats["by_source"].items()):
            print(f"    {source}: {count}")
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
