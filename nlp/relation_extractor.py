"""
Relation Extractor for Vietnam Football Knowledge Graph Enrichment

This module extracts relationships between entities from Vietnamese text
using pattern-based extraction with optional zero-shot fallback.

Relation Types:
- PLAYED_FOR: Player played for club
- COACHED: Coach coached team
- TRANSFERRED_TO: Player transferred to club
- SCORED_IN: Player scored in match/competition
- DEFEATED: Team defeated another team
- COMPETED_IN: Team competed in competition
- PLAYS_AT: Club plays at stadium
- BORN_IN: Person born in location
- CAPTAINED: Player captained team
- WON_AWARD: Person won award
- TEAMMATE_OF: Players were teammates

Usage:
    python -m nlp.relation_extractor --process-all
    python -m nlp.relation_extractor --sentence "Công Phượng ghi bàn cho HAGL"
"""

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import BASE_DIR, DATA_DIR

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

# Relation types and their argument type constraints
RELATION_TYPES = {
    "PLAYED_FOR": {
        "subject_types": ["PLAYER"],
        "object_types": ["CLUB", "NATIONAL_TEAM"],
        "description": "Player played for a club or national team",
    },
    "COACHED": {
        "subject_types": ["COACH"],
        "object_types": ["CLUB", "NATIONAL_TEAM"],
        "description": "Coach coached a team",
    },
    "TRANSFERRED_TO": {
        "subject_types": ["PLAYER"],
        "object_types": ["CLUB"],
        "description": "Player transferred to a club",
    },
    "SCORED_IN": {
        "subject_types": ["PLAYER"],
        "object_types": ["CLUB", "NATIONAL_TEAM", "COMPETITION", "EVENT"],
        "description": "Player scored in a match or competition",
    },
    "DEFEATED": {
        "subject_types": ["CLUB", "NATIONAL_TEAM"],
        "object_types": ["CLUB", "NATIONAL_TEAM"],
        "description": "Team defeated another team",
    },
    "COMPETED_IN": {
        "subject_types": ["CLUB", "NATIONAL_TEAM", "PLAYER"],
        "object_types": ["COMPETITION", "EVENT"],
        "description": "Entity competed in a competition",
    },
    "PLAYS_AT": {
        "subject_types": ["CLUB"],
        "object_types": ["STADIUM"],
        "description": "Club plays at a stadium",
    },
    "BORN_IN": {
        "subject_types": ["PLAYER", "COACH"],
        "object_types": ["PROVINCE"],
        "description": "Person was born in a location",
    },
    "CAPTAINED": {
        "subject_types": ["PLAYER"],
        "object_types": ["CLUB", "NATIONAL_TEAM"],
        "description": "Player was captain of a team",
    },
    "WON_AWARD": {
        "subject_types": ["PLAYER", "COACH"],
        "object_types": ["EVENT"],  # Award names treated as events
        "description": "Person won an award",
    },
    "TEAMMATE_OF": {
        "subject_types": ["PLAYER"],
        "object_types": ["PLAYER"],
        "description": "Players were teammates",
    },
}

# =============================================================================
# VIETNAMESE RELATION PATTERNS
# =============================================================================

# Pattern format: (regex_pattern, relation_type, subject_group, object_group, confidence)
# Groups refer to regex capture groups (1-indexed)

RELATION_PATTERNS = [
    # PLAYED_FOR patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:chơi|thi đấu|khoác áo)\s+(?:cho|tại|ở)\s+(\w+(?:\s+\w+)*)', 
     "PLAYED_FOR", 1, 2, 0.85),
    (r'(\w+(?:\s+\w+)*)\s+là\s+cầu\s+thủ\s+(?:của\s+)?(\w+(?:\s+\w+)*)',
     "PLAYED_FOR", 1, 2, 0.80),
    (r'cầu\s+thủ\s+(\w+(?:\s+\w+)*)\s+(?:của|thuộc)\s+(\w+(?:\s+\w+)*)',
     "PLAYED_FOR", 1, 2, 0.82),
    (r'(\w+(?:\s+\w+)*)\s+(?:gia nhập|đến|sang)\s+(\w+(?:\s+\w+)*)\s+(?:năm|từ|vào)',
     "PLAYED_FOR", 1, 2, 0.78),
    
    # COACHED patterns
    (r'(?:HLV|huấn luyện viên)\s+(\w+(?:\s+\w+)*)\s+(?:dẫn dắt|huấn luyện)\s+(\w+(?:\s+\w+)*)',
     "COACHED", 1, 2, 0.88),
    (r'(\w+(?:\s+\w+)*)\s+(?:làm|là)\s+(?:HLV|huấn luyện viên)\s+(?:của\s+)?(\w+(?:\s+\w+)*)',
     "COACHED", 1, 2, 0.85),
    (r'(\w+(?:\s+\w+)*)\s+(?:dẫn dắt|huấn luyện|cầm quân)\s+(\w+(?:\s+\w+)*)',
     "COACHED", 1, 2, 0.80),
    
    # TRANSFERRED_TO patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:chuyển|chuyển nhượng)\s+(?:đến|sang|về)\s+(\w+(?:\s+\w+)*)',
     "TRANSFERRED_TO", 1, 2, 0.88),
    (r'(\w+(?:\s+\w+)*)\s+(?:gia nhập|cập bến)\s+(\w+(?:\s+\w+)*)',
     "TRANSFERRED_TO", 1, 2, 0.85),
    (r'(\w+(?:\s+\w+)*)\s+(?:rời|chia tay)\s+\w+(?:\s+\w+)*\s+(?:đến|sang)\s+(\w+(?:\s+\w+)*)',
     "TRANSFERRED_TO", 1, 2, 0.82),
    
    # SCORED_IN patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:ghi bàn|lập công|sút tung lưới)\s+.*?(?:cho|trận gặp|vs\.?)\s+(\w+(?:\s+\w+)*)',
     "SCORED_IN", 1, 2, 0.85),
    (r'bàn\s+thắng\s+của\s+(\w+(?:\s+\w+)*)\s+.*?(?:vào lưới|trước)\s+(\w+(?:\s+\w+)*)',
     "SCORED_IN", 1, 2, 0.82),
    (r'(\w+(?:\s+\w+)*)\s+(?:ghi|có)\s+\d+\s+bàn\s+.*?(\w+(?:\s+\w+)*)',
     "SCORED_IN", 1, 2, 0.75),
    
    # DEFEATED patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:thắng|đánh bại|hạ|vượt qua)\s+(\w+(?:\s+\w+)*)',
     "DEFEATED", 1, 2, 0.85),
    (r'(\w+(?:\s+\w+)*)\s+(?:chiến thắng|giành chiến thắng)\s+(?:trước\s+)?(\w+(?:\s+\w+)*)',
     "DEFEATED", 1, 2, 0.85),
    (r'(\w+(?:\s+\w+)*)\s+(?:thua|để thua|gục ngã trước)\s+(\w+(?:\s+\w+)*)',
     "DEFEATED", 2, 1, 0.85),  # Note: reversed subject/object
    
    # COMPETED_IN patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:tham dự|tham gia|góp mặt)\s+(?:tại|ở|trong)?\s*(\w+(?:\s+\w+)*)',
     "COMPETED_IN", 1, 2, 0.80),
    (r'(\w+(?:\s+\w+)*)\s+(?:thi đấu|tranh tài)\s+(?:tại|ở)\s+(\w+(?:\s+\w+)*)',
     "COMPETED_IN", 1, 2, 0.82),
    (r'(\w+(?:\s+\w+)*)\s+(?:vô địch|đoạt chức vô địch)\s+(\w+(?:\s+\w+)*)',
     "COMPETED_IN", 1, 2, 0.88),
    
    # PLAYS_AT patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:chơi|thi đấu|sân nhà)\s+(?:tại|ở|trên)\s+(?:sân\s+)?(\w+(?:\s+\w+)*)',
     "PLAYS_AT", 1, 2, 0.82),
    (r'sân\s+(?:nhà\s+)?(?:của\s+)?(\w+(?:\s+\w+)*)\s+(?:là|:)\s+(\w+(?:\s+\w+)*)',
     "PLAYS_AT", 1, 2, 0.85),
    
    # BORN_IN patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:sinh|sinh ra|được sinh)\s+(?:tại|ở|ra tại)\s+(\w+(?:\s+\w+)*)',
     "BORN_IN", 1, 2, 0.90),
    (r'(\w+(?:\s+\w+)*)\s+(?:quê|quê quán)\s+(?:tại|ở|:)?\s*(\w+(?:\s+\w+)*)',
     "BORN_IN", 1, 2, 0.85),
    
    # CAPTAINED patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:là\s+)?(?:đội trưởng|thủ quân|đeo băng đội trưởng)\s+(?:của\s+)?(\w+(?:\s+\w+)*)',
     "CAPTAINED", 1, 2, 0.88),
    (r'(?:đội trưởng|thủ quân)\s+(\w+(?:\s+\w+)*)\s+(?:của\s+)?(\w+(?:\s+\w+)*)',
     "CAPTAINED", 1, 2, 0.85),
    
    # WON_AWARD patterns
    (r'(\w+(?:\s+\w+)*)\s+(?:giành|đoạt|nhận)\s+(?:giải\s+)?(\w+(?:\s+\w+)*)',
     "WON_AWARD", 1, 2, 0.78),
    (r'(\w+(?:\s+\w+)*)\s+(?:được trao|được vinh danh)\s+(\w+(?:\s+\w+)*)',
     "WON_AWARD", 1, 2, 0.80),
]


@dataclass
class Relation:
    """Represents an extracted relation."""
    subject_text: str
    subject_type: str
    predicate: str
    object_text: str
    object_type: str
    confidence: float
    subject_wiki_id: Optional[int] = None
    object_wiki_id: Optional[int] = None
    context: str = ""
    source: str = "pattern"  # "pattern", "zero_shot"
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "subject": {
                "text": self.subject_text,
                "type": self.subject_type,
                "wiki_id": self.subject_wiki_id,
            },
            "predicate": self.predicate,
            "object": {
                "text": self.object_text,
                "type": self.object_type,
                "wiki_id": self.object_wiki_id,
            },
            "confidence": self.confidence,
            "context": self.context,
            "source": self.source,
            "metadata": self.metadata,
        }


class PatternRelationExtractor:
    """
    Pattern-based relation extraction for Vietnamese football text.
    
    Uses regex patterns with entity type constraints to extract
    relationships between entities.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.6,
    ):
        """
        Initialize the pattern extractor.
        
        Args:
            confidence_threshold: Minimum confidence for relations
        """
        self.confidence_threshold = confidence_threshold
        
        # Compile patterns
        self.compiled_patterns = []
        for pattern, rel_type, subj_group, obj_group, conf in RELATION_PATTERNS:
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.UNICODE)
                self.compiled_patterns.append({
                    "pattern": compiled,
                    "relation_type": rel_type,
                    "subject_group": subj_group,
                    "object_group": obj_group,
                    "base_confidence": conf,
                })
            except re.error as e:
                logger.warning(f"Invalid pattern '{pattern}': {e}")
    
    def extract(
        self,
        sentence: str,
        entities: List[Dict],
    ) -> List[Relation]:
        """
        Extract relations from a sentence with recognized entities.
        
        Args:
            sentence: Input sentence
            entities: List of recognized entities (from NER)
            
        Returns:
            List of extracted relations
        """
        relations = []
        
        if len(entities) < 2:
            return relations
        
        # Build entity lookup by text
        entity_lookup = {}
        for entity in entities:
            text = entity.get("text", "").lower()
            entity_lookup[text] = entity
        
        # Try each pattern
        for pattern_info in self.compiled_patterns:
            pattern = pattern_info["pattern"]
            rel_type = pattern_info["relation_type"]
            subj_group = pattern_info["subject_group"]
            obj_group = pattern_info["object_group"]
            base_conf = pattern_info["base_confidence"]
            
            for match in pattern.finditer(sentence):
                try:
                    subject_text = match.group(subj_group).strip()
                    object_text = match.group(obj_group).strip()
                    
                    # Look up entities
                    subject_entity = self._find_entity(subject_text, entity_lookup, entities)
                    object_entity = self._find_entity(object_text, entity_lookup, entities)
                    
                    if not subject_entity or not object_entity:
                        continue
                    
                    # Check type constraints
                    rel_constraints = RELATION_TYPES.get(rel_type, {})
                    valid_subj_types = rel_constraints.get("subject_types", [])
                    valid_obj_types = rel_constraints.get("object_types", [])
                    
                    subj_type = subject_entity.get("type", "")
                    obj_type = object_entity.get("type", "")
                    
                    # Adjust confidence based on type match
                    confidence = base_conf
                    if valid_subj_types and subj_type not in valid_subj_types:
                        confidence *= 0.7  # Penalty for type mismatch
                    if valid_obj_types and obj_type not in valid_obj_types:
                        confidence *= 0.7
                    
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Extract context (surrounding text)
                    start = max(0, match.start() - 20)
                    end = min(len(sentence), match.end() + 20)
                    context = sentence[start:end]
                    
                    relations.append(Relation(
                        subject_text=subject_entity.get("text", subject_text),
                        subject_type=subj_type or "UNKNOWN",
                        predicate=rel_type,
                        object_text=object_entity.get("text", object_text),
                        object_type=obj_type or "UNKNOWN",
                        confidence=confidence,
                        subject_wiki_id=subject_entity.get("wiki_id"),
                        object_wiki_id=object_entity.get("wiki_id"),
                        context=context,
                        source="pattern",
                    ))
                    
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Pattern match error: {e}")
                    continue
        
        return relations
    
    def _find_entity(
        self,
        text: str,
        entity_lookup: Dict[str, Dict],
        entities: List[Dict],
    ) -> Optional[Dict]:
        """
        Find matching entity for extracted text.
        
        Args:
            text: Text to match
            entity_lookup: Dictionary of entities by text
            entities: List of all entities
            
        Returns:
            Matching entity or None
        """
        # Exact match
        text_lower = text.lower()
        if text_lower in entity_lookup:
            return entity_lookup[text_lower]
        
        # Partial match - check if text is contained in any entity
        for entity in entities:
            entity_text = entity.get("text", "").lower()
            if text_lower in entity_text or entity_text in text_lower:
                return entity
        
        # No match found - return a minimal entity dict
        return {"text": text, "type": "UNKNOWN"}


class ZeroShotRelationExtractor:
    """
    Zero-shot relation extraction using generative models.
    
    Uses a multilingual model to extract relations from text
    when pattern-based extraction fails or has low confidence.
    """
    
    def __init__(
        self,
        model_name: str = "facebook/mbart-large-50",
        device: str = "auto",
    ):
        """
        Initialize zero-shot extractor.
        
        Args:
            model_name: Hugging Face model name
            device: Device for inference
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the model (lazy loading)."""
        if self._initialized:
            return True
        
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            
            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"Loading zero-shot model on {self.device}...")
            
            # For Vietnamese, we could use a multilingual model
            # or a Vietnamese-specific model like VietAI/vit5
            try:
                self.tokenizer = AutoTokenizer.from_pretrained("VietAI/vit5-base")
                self.model = AutoModelForSeq2SeqLM.from_pretrained("VietAI/vit5-base")
            except Exception:
                logger.warning("VietAI/vit5 not available, zero-shot disabled")
                return False
            
            if self.device == "cuda":
                self.model = self.model.cuda()
            
            self._initialized = True
            return True
            
        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing zero-shot model: {e}")
            return False
    
    def extract(
        self,
        sentence: str,
        entity1: Dict,
        entity2: Dict,
    ) -> List[Relation]:
        """
        Extract relations between two entities using zero-shot inference.
        
        Args:
            sentence: Input sentence
            entity1: First entity dict
            entity2: Second entity dict
            
        Returns:
            List of extracted relations
        """
        if not self._initialized:
            if not self.initialize():
                return []
        
        # This is a simplified implementation
        # A full implementation would use the model to generate relation predictions
        
        # For now, return empty (rely on pattern-based)
        return []


class RelationExtractor:
    """
    Main relation extraction class combining pattern-based and zero-shot methods.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.6,
        use_zero_shot: bool = False,
        device: str = "auto",
    ):
        """
        Initialize the relation extractor.
        
        Args:
            confidence_threshold: Minimum confidence for relations
            use_zero_shot: Enable zero-shot extraction
            device: Device for model inference
        """
        self.confidence_threshold = confidence_threshold
        
        # Initialize components
        self.pattern_extractor = PatternRelationExtractor(confidence_threshold)
        self.zero_shot_extractor = ZeroShotRelationExtractor(device=device) if use_zero_shot else None
        
        # Ensure output directory exists
        ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
    
    def extract(
        self,
        sentence: str,
        entities: List[Dict],
    ) -> List[Relation]:
        """
        Extract relations from a sentence.
        
        Args:
            sentence: Input sentence
            entities: List of recognized entities
            
        Returns:
            List of extracted relations
        """
        relations = []
        
        # 1. Pattern-based extraction
        pattern_relations = self.pattern_extractor.extract(sentence, entities)
        relations.extend(pattern_relations)
        
        # 2. Zero-shot for entity pairs without pattern matches (if enabled)
        if self.zero_shot_extractor and len(entities) >= 2:
            # Find entity pairs not covered by pattern extraction
            covered_pairs = set()
            for rel in pattern_relations:
                covered_pairs.add((rel.subject_text.lower(), rel.object_text.lower()))
                covered_pairs.add((rel.object_text.lower(), rel.subject_text.lower()))
            
            for i, e1 in enumerate(entities):
                for e2 in entities[i+1:]:
                    pair = (e1.get("text", "").lower(), e2.get("text", "").lower())
                    if pair not in covered_pairs:
                        zero_shot_relations = self.zero_shot_extractor.extract(
                            sentence, e1, e2
                        )
                        relations.extend(zero_shot_relations)
        
        # Remove duplicates
        seen = set()
        unique_relations = []
        for rel in relations:
            key = (rel.subject_text.lower(), rel.predicate, rel.object_text.lower())
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)
        
        return unique_relations
    
    def process_entities_file(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
        max_records: int = -1,
    ) -> Dict[str, int]:
        """
        Process recognized entities file and extract relations.
        
        Args:
            input_file: Input JSONL file with recognized entities
            output_file: Output JSONL file for relations
            max_records: Maximum records to process (-1 for all)
            
        Returns:
            Statistics dict
        """
        stats = {
            "records_processed": 0,
            "relations_found": 0,
            "by_type": {},
            "by_confidence": {"high": 0, "medium": 0, "low": 0},
        }
        
        if output_file is None:
            output_file = ENRICHMENT_DIR / "extracted_relations.jsonl"
        
        # Count total lines
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        if max_records > 0:
            total_lines = min(total_lines, max_records)
        
        with open(input_file, 'r', encoding='utf-8') as in_f, \
             open(output_file, 'w', encoding='utf-8') as out_f:
            
            for i, line in enumerate(tqdm(in_f, total=total_lines, desc="Extracting relations")):
                if max_records > 0 and i >= max_records:
                    break
                
                try:
                    record = json.loads(line)
                    sentence = record.get("sentence", "")
                    entities = record.get("entities", [])
                    
                    if not sentence or len(entities) < 2:
                        continue
                    
                    # Extract relations
                    relations = self.extract(sentence, entities)
                    
                    if relations:
                        # Build output record
                        output_record = {
                            "sentence_id": record.get("sentence_id"),
                            "wiki_id": record.get("wiki_id"),
                            "page_title": record.get("page_title"),
                            "sentence": sentence,
                            "relations": [r.to_dict() for r in relations],
                            "date_extracted": datetime.utcnow().isoformat(),
                        }
                        
                        out_f.write(json.dumps(output_record, ensure_ascii=False) + '\n')
                        
                        # Update stats
                        stats["relations_found"] += len(relations)
                        
                        for rel in relations:
                            # By type
                            if rel.predicate not in stats["by_type"]:
                                stats["by_type"][rel.predicate] = 0
                            stats["by_type"][rel.predicate] += 1
                            
                            # By confidence
                            if rel.confidence >= 0.85:
                                stats["by_confidence"]["high"] += 1
                            elif rel.confidence >= 0.70:
                                stats["by_confidence"]["medium"] += 1
                            else:
                                stats["by_confidence"]["low"] += 1
                    
                    stats["records_processed"] += 1
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at line {i}: {e}")
                except Exception as e:
                    logger.error(f"Error processing line {i}: {e}")
        
        logger.info(f"Processed {stats['records_processed']} records, found {stats['relations_found']} relations")
        
        return stats
    
    def extract_single(
        self,
        sentence: str,
        entities: List[Dict],
    ) -> Dict:
        """
        Extract relations from a single sentence.
        
        Args:
            sentence: Input sentence
            entities: List of entity dicts
            
        Returns:
            Dict with relations
        """
        relations = self.extract(sentence, entities)
        
        return {
            "sentence": sentence,
            "relations": [r.to_dict() for r in relations],
            "date_extracted": datetime.utcnow().isoformat(),
        }


def main():
    """CLI entry point for relation extractor."""
    parser = argparse.ArgumentParser(
        description="Relation Extraction for Vietnam Football KG"
    )
    
    parser.add_argument(
        "--process-all",
        action="store_true",
        help="Process all recognized entities",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input JSONL file with recognized entities",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSONL file for relations",
    )
    parser.add_argument(
        "--sentence",
        type=str,
        help="Process a single sentence",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=-1,
        help="Maximum records to process",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.6,
        help="Minimum confidence threshold",
    )
    parser.add_argument(
        "--use-zero-shot",
        action="store_true",
        help="Enable zero-shot extraction (slower)",
    )
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = RelationExtractor(
        confidence_threshold=args.confidence_threshold,
        use_zero_shot=args.use_zero_shot,
    )
    
    if args.sentence:
        # For demo, create some mock entities
        # In practice, you'd first run NER on the sentence
        print(f"\n=== Processing Single Sentence ===")
        print(f"Input: {args.sentence}")
        print("\nNote: Run NER first to get entities, then extract relations.")
        print("Example with mock entities:")
        
        mock_entities = [
            {"text": "Công Phượng", "type": "PLAYER", "wiki_id": 1},
            {"text": "HAGL", "type": "CLUB", "wiki_id": 2},
        ]
        
        result = extractor.extract_single(args.sentence, mock_entities)
        
        print("\nRelations found:")
        for rel in result["relations"]:
            print(f"  ({rel['subject']['text']}) --[{rel['predicate']}]--> ({rel['object']['text']})")
            print(f"    Confidence: {rel['confidence']:.2f}")
        return
    
    if args.process_all:
        # Find input file
        input_file = Path(args.input) if args.input else ENRICHMENT_DIR / "recognized_entities.jsonl"
        output_file = Path(args.output) if args.output else None
        
        if not input_file.exists():
            print(f"Input file not found: {input_file}")
            print("Run entity_recognizer first.")
            return
        
        print(f"\n=== Extracting Relations ===")
        print(f"Input: {input_file}")
        print(f"Output: {output_file or ENRICHMENT_DIR / 'extracted_relations.jsonl'}")
        
        stats = extractor.process_entities_file(
            input_file=input_file,
            output_file=output_file,
            max_records=args.max_records,
        )
        
        print(f"\nResults:")
        print(f"  Records processed: {stats['records_processed']}")
        print(f"  Relations found: {stats['relations_found']}")
        print(f"\n  By type:")
        for rel_type, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
            print(f"    {rel_type}: {count}")
        print(f"\n  By confidence:")
        print(f"    High (≥0.85): {stats['by_confidence']['high']}")
        print(f"    Medium (0.70-0.85): {stats['by_confidence']['medium']}")
        print(f"    Low (<0.70): {stats['by_confidence']['low']}")
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
