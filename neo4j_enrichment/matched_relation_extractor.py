"""
Relation Extractor from Matched Entities

This module extracts relations between EXISTING entities found in sentences.
Instead of relying on NER-based relation extraction, we:
1. Find sentences with multiple matched entities
2. Apply pattern-based rules to extract relations
3. Only output relations between entities that exist in DB

This is MUCH more accurate than general RE because:
- Both entities are verified to exist in DB
- Patterns are specific to Vietnamese football context
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from tqdm import tqdm

from .strict_enrichment import ExistingEntityMatcher

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ENRICHMENT_DIR = DATA_DIR / "enrichment"


@dataclass
class ExtractedRelation:
    """A relation extracted from text."""
    subject_text: str
    subject_type: str
    subject_wiki_id: Optional[int]
    predicate: str
    object_text: str
    object_type: str
    object_wiki_id: Optional[int]
    confidence: float
    context: str
    pattern_name: str


# Relation patterns for Vietnamese football
# Format: (pattern_name, regex, subject_type, predicate, object_type)
RELATION_PATTERNS = [
    # PLAYED_FOR patterns
    (
        "played_for_explicit",
        r"(?P<player>\S+(?:\s+\S+){0,3})\s+(?:thi đấu|chơi|khoác áo)\s+(?:cho\s+)?(?:câu lạc bộ\s+)?(?P<club>\S+(?:\s+\S+){0,3})",
        "PLAYER", "PLAYED_FOR", "CLUB"
    ),
    (
        "player_of_club",
        r"(?:cầu thủ|tiền đạo|tiền vệ|hậu vệ|thủ môn)\s+(?:của\s+)?(?P<club>\S+(?:\s+\S+){0,3})",
        "PLAYER", "PLAYED_FOR", "CLUB"
    ),
    
    # COMPETED_IN patterns
    (
        "competed_in_tournament",
        r"(?:tham gia|thi đấu tại|góp mặt tại)\s+(?P<competition>\S+(?:\s+\S+){0,5})",
        "PLAYER", "COMPETED_IN", "COMPETITION"
    ),
    (
        "won_tournament",
        r"(?:vô địch|giành chức vô địch|đoạt|chiến thắng)\s+(?P<competition>\S+(?:\s+\S+){0,5})",
        "PLAYER", "COMPETED_IN", "COMPETITION"
    ),
    
    # COACHED patterns
    (
        "coached_team",
        r"(?:huấn luyện viên|HLV)\s+(?P<coach>\S+(?:\s+\S+){0,3})\s+(?:dẫn dắt|huấn luyện)\s+(?P<team>\S+(?:\s+\S+){0,3})",
        "COACH", "COACHED", "CLUB"
    ),
    
    # PLAYED_FOR_NATIONAL patterns
    (
        "national_team_player",
        r"(?:khoác áo|đại diện cho|cầu thủ)\s+(?P<national_team>đội tuyển\s+\S+(?:\s+\S+){0,3})",
        "PLAYER", "PLAYED_FOR_NATIONAL", "NATIONAL_TEAM"
    ),
    
    # DEFEATED patterns
    (
        "defeated_team",
        r"(?P<team1>\S+(?:\s+\S+){0,3})\s+(?:đánh bại|thắng|chiến thắng)\s+(?P<team2>\S+(?:\s+\S+){0,3})",
        "CLUB", "DEFEATED", "CLUB"
    ),
    
    # TRANSFERRED_TO patterns
    (
        "transferred_to",
        r"(?:chuyển đến|chuyển sang|gia nhập)\s+(?P<club>\S+(?:\s+\S+){0,3})",
        "PLAYER", "TRANSFERRED_TO", "CLUB"
    ),
]


class MatchedEntityRelationExtractor:
    """Extract relations between matched entities in sentences."""
    
    def __init__(self):
        self.entity_matcher = ExistingEntityMatcher()
        self.stats = defaultdict(int)
    
    def find_matched_entities_in_sentence(
        self, 
        entities: List[dict],
        sentence: str,
    ) -> List[dict]:
        """
        Filter entities that match existing database entries.
        
        Args:
            entities: List of entity dicts from NER
            sentence: The sentence text
            
        Returns:
            List of matched entities with their DB info
        """
        matched = []
        
        for entity in entities:
            text = entity.get("text", "")
            entity_type = entity.get("type", "")
            
            # Try to find match in DB
            db_match = self.entity_matcher.find_match(text, entity_type)
            
            if db_match:
                matched.append({
                    "text": text,
                    "type": entity_type,
                    "db_match": db_match,
                    "wiki_id": db_match.get("wiki_id"),
                    "start": entity.get("start", 0),
                    "end": entity.get("end", 0),
                })
        
        return matched
    
    def extract_co_occurrence_relations(
        self,
        matched_entities: List[dict],
        sentence: str,
        page_title: str = "",
    ) -> List[ExtractedRelation]:
        """
        Extract relations based on co-occurrence in sentence.
        
        If a PLAYER and CLUB appear in same sentence about football,
        high chance there's a PLAYED_FOR relation.
        """
        relations = []
        
        # Group entities by type
        by_type = defaultdict(list)
        for entity in matched_entities:
            by_type[entity["type"]].append(entity)
        
        # PLAYER + CLUB in same sentence -> potential PLAYED_FOR
        for player in by_type.get("PLAYER", []):
            for club in by_type.get("CLUB", []):
                # Check context clues
                sentence_lower = sentence.lower()
                if any(kw in sentence_lower for kw in ["thi đấu", "chơi cho", "khoác áo", "cầu thủ", "gia nhập"]):
                    relations.append(ExtractedRelation(
                        subject_text=player["text"],
                        subject_type="PLAYER",
                        subject_wiki_id=player["wiki_id"],
                        predicate="PLAYED_FOR",
                        object_text=club["text"],
                        object_type="CLUB",
                        object_wiki_id=club["wiki_id"],
                        confidence=0.75,
                        context=sentence[:200],
                        pattern_name="co_occurrence_player_club",
                    ))
                    self.stats["co_occurrence_player_club"] += 1
        
        # PLAYER + NATIONAL_TEAM -> potential PLAYED_FOR_NATIONAL
        for player in by_type.get("PLAYER", []):
            for team in by_type.get("NATIONAL_TEAM", []):
                sentence_lower = sentence.lower()
                if any(kw in sentence_lower for kw in ["đội tuyển", "quốc gia", "khoác áo", "tuyển"]):
                    relations.append(ExtractedRelation(
                        subject_text=player["text"],
                        subject_type="PLAYER",
                        subject_wiki_id=player["wiki_id"],
                        predicate="PLAYED_FOR_NATIONAL",
                        object_text=team["text"],
                        object_type="NATIONAL_TEAM",
                        object_wiki_id=team["wiki_id"],
                        confidence=0.80,
                        context=sentence[:200],
                        pattern_name="co_occurrence_player_national",
                    ))
                    self.stats["co_occurrence_player_national"] += 1
        
        # PLAYER + COMPETITION -> potential COMPETED_IN
        for player in by_type.get("PLAYER", []):
            for comp in by_type.get("COMPETITION", []):
                sentence_lower = sentence.lower()
                if any(kw in sentence_lower for kw in ["vô địch", "tham gia", "thi đấu", "giải", "cup"]):
                    relations.append(ExtractedRelation(
                        subject_text=player["text"],
                        subject_type="PLAYER",
                        subject_wiki_id=player["wiki_id"],
                        predicate="COMPETED_IN",
                        object_text=comp["text"],
                        object_type="COMPETITION",
                        object_wiki_id=comp["wiki_id"],
                        confidence=0.70,
                        context=sentence[:200],
                        pattern_name="co_occurrence_player_competition",
                    ))
                    self.stats["co_occurrence_player_competition"] += 1
        
        # CLUB + COMPETITION -> potential COMPETES_IN
        for club in by_type.get("CLUB", []):
            for comp in by_type.get("COMPETITION", []):
                sentence_lower = sentence.lower()
                if any(kw in sentence_lower for kw in ["tham gia", "thi đấu", "giải", "vô địch"]):
                    relations.append(ExtractedRelation(
                        subject_text=club["text"],
                        subject_type="CLUB",
                        subject_wiki_id=club["wiki_id"],
                        predicate="COMPETES_IN",
                        object_text=comp["text"],
                        object_type="COMPETITION",
                        object_wiki_id=comp["wiki_id"],
                        confidence=0.70,
                        context=sentence[:200],
                        pattern_name="co_occurrence_club_competition",
                    ))
                    self.stats["co_occurrence_club_competition"] += 1
        
        # COACH + CLUB -> potential COACHED
        for coach in by_type.get("COACH", []):
            for club in by_type.get("CLUB", []):
                sentence_lower = sentence.lower()
                if any(kw in sentence_lower for kw in ["huấn luyện", "dẫn dắt", "HLV", "huấn luyện viên"]):
                    relations.append(ExtractedRelation(
                        subject_text=coach["text"],
                        subject_type="COACH",
                        subject_wiki_id=coach["wiki_id"],
                        predicate="COACHED",
                        object_text=club["text"],
                        object_type="CLUB",
                        object_wiki_id=club["wiki_id"],
                        confidence=0.75,
                        context=sentence[:200],
                        pattern_name="co_occurrence_coach_club",
                    ))
                    self.stats["co_occurrence_coach_club"] += 1
        
        return relations
    
    def process_validated_entities(
        self,
        input_file: Path,
    ) -> List[ExtractedRelation]:
        """
        Process validated entities file and extract relations.
        
        Args:
            input_file: Path to validated_entities.jsonl
            
        Returns:
            List of extracted relations
        """
        all_relations = []
        
        if not input_file.exists():
            print(f"File not found: {input_file}")
            return all_relations
        
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, total=total_lines, desc="Extracting relations"):
                try:
                    record = json.loads(line)
                    entities = record.get("entities", [])
                    sentence = record.get("sentence", "")
                    page_title = record.get("page_title", "")
                    
                    self.stats["total_sentences"] += 1
                    
                    # Find matched entities
                    matched = self.find_matched_entities_in_sentence(entities, sentence)
                    
                    if len(matched) >= 2:
                        self.stats["sentences_with_multiple_entities"] += 1
                        
                        # Extract relations
                        relations = self.extract_co_occurrence_relations(
                            matched, sentence, page_title
                        )
                        all_relations.extend(relations)
                
                except Exception as e:
                    continue
        
        return all_relations
    
    def get_stats(self) -> dict:
        """Get extraction statistics."""
        return dict(self.stats)


def main():
    """Run relation extraction on validated entities."""
    print("=" * 60)
    print("MATCHED ENTITY RELATION EXTRACTOR")
    print("=" * 60)
    
    extractor = MatchedEntityRelationExtractor()
    
    input_file = ENRICHMENT_DIR / "validated_entities.jsonl"
    output_file = ENRICHMENT_DIR / "matched_relations.jsonl"
    
    print(f"\nInput: {input_file}")
    print(f"Output: {output_file}")
    
    # Extract relations
    relations = extractor.process_validated_entities(input_file)
    
    # Deduplicate
    seen = set()
    unique_relations = []
    for rel in relations:
        key = (rel.subject_wiki_id, rel.predicate, rel.object_wiki_id)
        if key not in seen:
            seen.add(key)
            unique_relations.append(rel)
    
    # Save
    ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for rel in unique_relations:
            data = {
                "subject": {
                    "text": rel.subject_text,
                    "type": rel.subject_type,
                    "wiki_id": rel.subject_wiki_id,
                },
                "predicate": rel.predicate,
                "object": {
                    "text": rel.object_text,
                    "type": rel.object_type,
                    "wiki_id": rel.object_wiki_id,
                },
                "confidence": rel.confidence,
                "context": rel.context,
                "pattern": rel.pattern_name,
            }
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    
    # Stats
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total relations extracted: {len(relations)}")
    print(f"Unique relations: {len(unique_relations)}")
    print(f"\nBy pattern:")
    stats = extractor.get_stats()
    for key, value in sorted(stats.items()):
        if key.startswith("co_occurrence"):
            print(f"  {key}: {value}")
    
    print(f"\nSaved to: {output_file}")
    
    # Show sample
    print("\n" + "=" * 60)
    print("SAMPLE RELATIONS")
    print("=" * 60)
    for rel in unique_relations[:10]:
        print(f"  ({rel.subject_text}) --[{rel.predicate}]--> ({rel.object_text})")
        print(f"    Pattern: {rel.pattern_name}, Confidence: {rel.confidence}")


if __name__ == "__main__":
    main()
