"""
Validation Module for Vietnam Football Knowledge Graph Enrichment

This module validates extracted entities and relations:
- Deduplication against existing knowledge graph
- Consistency checks (temporal, type constraints)
- Conflict detection and resolution
- Quality reporting

Usage:
    python -m enrichment.validation --validate-all
    python -m enrichment.validation --generate-report
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
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
REPORTS_DIR = BASE_DIR / "reports"

# Validation thresholds
ENTITY_MATCH_THRESHOLD = 0.90
RELATION_MATCH_THRESHOLD = 0.95

# Relation type constraints for consistency checking
RELATION_CONSTRAINTS = {
    "PLAYED_FOR": {
        "temporal": True,  # Can have dates
        "reversible": False,
    },
    "COACHED": {
        "temporal": True,
        "reversible": False,
    },
    "TRANSFERRED_TO": {
        "temporal": True,
        "implies": ["PLAYED_FOR"],  # Transfer implies playing
    },
    "DEFEATED": {
        "temporal": True,
        "reversible": False,
        "symmetric_inverse": "LOST_TO",
    },
    "BORN_IN": {
        "temporal": False,
        "unique": True,  # Only one birthplace
    },
}


@dataclass
class ValidationResult:
    """Result of validating a single entity or relation."""
    item_type: str  # "entity" or "relation"
    item_id: str
    status: str  # "valid", "duplicate", "conflict", "invalid"
    confidence: float
    issues: List[str] = field(default_factory=list)
    matched_existing: Optional[Dict] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "item_type": self.item_type,
            "item_id": self.item_id,
            "status": self.status,
            "confidence": self.confidence,
            "issues": self.issues,
            "matched_existing": self.matched_existing,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationReport:
    """Summary report of validation results."""
    total_entities: int = 0
    total_relations: int = 0
    
    # Entity stats
    valid_entities: int = 0
    duplicate_entities: int = 0
    new_entities: int = 0
    invalid_entities: int = 0
    
    # Relation stats
    valid_relations: int = 0
    duplicate_relations: int = 0
    new_relations: int = 0
    conflict_relations: int = 0
    invalid_relations: int = 0
    
    # Confidence distribution
    high_confidence: int = 0  # >= 0.85
    medium_confidence: int = 0  # 0.70-0.85
    low_confidence: int = 0  # < 0.70
    
    # Detailed issues
    issues: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total_entities": self.total_entities,
                "total_relations": self.total_relations,
                "entities": {
                    "valid": self.valid_entities,
                    "duplicate": self.duplicate_entities,
                    "new_candidates": self.new_entities,
                    "invalid": self.invalid_entities,
                },
                "relations": {
                    "valid": self.valid_relations,
                    "duplicate": self.duplicate_relations,
                    "new": self.new_relations,
                    "conflicts": self.conflict_relations,
                    "invalid": self.invalid_relations,
                },
                "confidence_distribution": {
                    "high": self.high_confidence,
                    "medium": self.medium_confidence,
                    "low": self.low_confidence,
                },
            },
            "issues": self.issues,
            "generated_at": datetime.utcnow().isoformat(),
        }


class ExistingKnowledgeGraph:
    """
    Interface to the existing knowledge graph for validation.
    
    Loads entities and relations from processed CSV files and Neo4j.
    """
    
    def __init__(self):
        """Initialize with existing data."""
        self.entities: Dict[str, List[Dict]] = {}  # type -> list of entities
        self.relations: Dict[str, List[Dict]] = {}  # type -> list of relations
        self.entity_index: Dict[str, Dict] = {}  # normalized_name -> entity
        
        self._load_existing_data()
    
    def _load_existing_data(self) -> None:
        """Load existing entities from CSV files."""
        entity_files = {
            "PLAYER": PROCESSED_DATA_DIR / "players_clean.csv",
            "COACH": PROCESSED_DATA_DIR / "coaches_clean.csv",
            "CLUB": PROCESSED_DATA_DIR / "clubs_clean.csv",
            "NATIONAL_TEAM": PROCESSED_DATA_DIR / "national_teams_clean.csv",
            "STADIUM": PROCESSED_DATA_DIR / "stadiums_clean.csv",
            "COMPETITION": PROCESSED_DATA_DIR / "competitions_clean.csv",
            "PROVINCE": PROCESSED_DATA_DIR / "provinces_reference.csv",
        }
        
        for entity_type, file_path in entity_files.items():
            if not file_path.exists():
                continue
            
            try:
                df = pd.read_csv(file_path)
                self.entities[entity_type] = []
                
                # Determine name column
                name_col = None
                for col in ["name", "full_name", "club_name", "stadium_name", "province"]:
                    if col in df.columns:
                        name_col = col
                        break
                
                if name_col is None:
                    continue
                
                for _, row in df.iterrows():
                    name = str(row[name_col]).strip()
                    if not name or name == "nan":
                        continue
                    
                    wiki_id = row.get("wiki_id", row.get("page_id", None))
                    if pd.isna(wiki_id):
                        wiki_id = None
                    
                    entity = {
                        "name": name,
                        "wiki_id": wiki_id,
                        "type": entity_type,
                    }
                    
                    self.entities[entity_type].append(entity)
                    
                    # Index by normalized name
                    norm_name = self._normalize(name)
                    self.entity_index[norm_name] = entity
                    
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        # Load existing relations from edge files
        edge_files = {
            "PLAYED_FOR": DATA_DIR / "edges" / "played_for.csv",
            "COACHED": DATA_DIR / "edges" / "coached.csv",
            "BORN_IN": DATA_DIR / "edges" / "born_in.csv",
            "TEAMMATE": DATA_DIR / "edges" / "teammate.csv",
        }
        
        for rel_type, file_path in edge_files.items():
            if not file_path.exists():
                continue
            
            try:
                df = pd.read_csv(file_path)
                self.relations[rel_type] = df.to_dict('records')
            except Exception as e:
                logger.warning(f"Error loading {file_path}: {e}")
        
        logger.info(f"Loaded {sum(len(v) for v in self.entities.values())} entities, "
                   f"{sum(len(v) for v in self.relations.values())} relations")
    
    def _normalize(self, text: str) -> str:
        """Normalize text for matching."""
        return ' '.join(text.lower().split())
    
    def find_entity(
        self,
        text: str,
        entity_type: Optional[str] = None,
    ) -> Optional[Tuple[Dict, float]]:
        """
        Find matching entity in existing graph.
        
        Args:
            text: Entity text to match
            entity_type: Optional type filter
            
        Returns:
            Tuple of (entity dict, match score) or None
        """
        try:
            from rapidfuzz import fuzz
        except ImportError:
            # Fallback to exact match
            norm_text = self._normalize(text)
            if norm_text in self.entity_index:
                return (self.entity_index[norm_text], 1.0)
            return None
        
        norm_text = self._normalize(text)
        
        # Exact match
        if norm_text in self.entity_index:
            entity = self.entity_index[norm_text]
            if entity_type is None or entity.get("type") == entity_type:
                return (entity, 1.0)
        
        # Fuzzy match
        best_match = None
        best_score = 0.0
        
        types_to_search = [entity_type] if entity_type else self.entities.keys()
        
        for etype in types_to_search:
            if etype not in self.entities:
                continue
            
            for entity in self.entities[etype]:
                norm_name = self._normalize(entity["name"])
                score = fuzz.token_set_ratio(norm_text, norm_name) / 100.0
                
                if score > best_score:
                    best_score = score
                    best_match = entity
        
        if best_match and best_score >= 0.85:
            return (best_match, best_score)
        
        return None
    
    def find_relation(
        self,
        subject_id: int,
        predicate: str,
        object_id: int,
    ) -> Optional[Dict]:
        """
        Find existing relation in graph.
        
        Args:
            subject_id: Subject wiki_id
            predicate: Relation type
            object_id: Object wiki_id
            
        Returns:
            Existing relation dict or None
        """
        if predicate not in self.relations:
            return None
        
        for rel in self.relations[predicate]:
            subj_key = rel.get("source_wiki_id", rel.get("from_wiki_id"))
            obj_key = rel.get("target_wiki_id", rel.get("to_wiki_id"))
            
            if subj_key == subject_id and obj_key == object_id:
                return rel
        
        return None


class EnrichmentValidator:
    """
    Main validation class for enrichment data.
    """
    
    def __init__(
        self,
        entity_match_threshold: float = ENTITY_MATCH_THRESHOLD,
        relation_match_threshold: float = RELATION_MATCH_THRESHOLD,
    ):
        """
        Initialize the validator.
        
        Args:
            entity_match_threshold: Threshold for entity matching
            relation_match_threshold: Threshold for relation matching
        """
        self.entity_match_threshold = entity_match_threshold
        self.relation_match_threshold = relation_match_threshold
        
        # Load existing knowledge graph
        self.kg = ExistingKnowledgeGraph()
        
        # Ensure output directories exist
        ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def validate_entity(
        self,
        entity: Dict,
    ) -> ValidationResult:
        """
        Validate a single entity.
        
        Args:
            entity: Entity dict from NER
            
        Returns:
            ValidationResult
        """
        text = entity.get("text", "")
        entity_type = entity.get("type", "UNKNOWN")
        confidence = entity.get("confidence", 0.0)
        wiki_id = entity.get("wiki_id")
        
        issues = []
        status = "valid"
        matched_existing = None
        
        # Check if already linked to existing entity
        if wiki_id is not None:
            status = "duplicate"
            matched_existing = {"wiki_id": wiki_id}
            return ValidationResult(
                item_type="entity",
                item_id=f"{entity_type}:{text}",
                status=status,
                confidence=confidence,
                matched_existing=matched_existing,
            )
        
        # Try to find match in existing graph
        match_result = self.kg.find_entity(text, entity_type)
        
        if match_result:
            matched_entity, match_score = match_result
            
            if match_score >= self.entity_match_threshold:
                status = "duplicate"
                matched_existing = matched_entity
            elif match_score >= 0.7:
                status = "possible_duplicate"
                matched_existing = matched_entity
                issues.append(f"Possible match: {matched_entity['name']} (score={match_score:.2f})")
            else:
                status = "new_candidate"
        else:
            status = "new_candidate"
        
        # Validate entity type
        if entity_type == "UNKNOWN":
            issues.append("Entity type unknown")
            status = "invalid" if status == "valid" else status
        
        # Check confidence
        if confidence < 0.5:
            issues.append(f"Low confidence: {confidence:.2f}")
        
        return ValidationResult(
            item_type="entity",
            item_id=f"{entity_type}:{text}",
            status=status,
            confidence=confidence,
            issues=issues,
            matched_existing=matched_existing,
        )
    
    def validate_relation(
        self,
        relation: Dict,
    ) -> ValidationResult:
        """
        Validate a single relation.
        
        Args:
            relation: Relation dict from RE
            
        Returns:
            ValidationResult
        """
        subject = relation.get("subject", {})
        predicate = relation.get("predicate", "")
        obj = relation.get("object", {})
        confidence = relation.get("confidence", 0.0)
        
        issues = []
        status = "valid"
        matched_existing = None
        
        subj_text = subject.get("text", "")
        subj_type = subject.get("type", "UNKNOWN")
        subj_wiki_id = subject.get("wiki_id")
        
        obj_text = obj.get("text", "")
        obj_type = obj.get("type", "UNKNOWN")
        obj_wiki_id = obj.get("wiki_id")
        
        # Check if both entities are linked
        if subj_wiki_id is None:
            issues.append(f"Subject not linked: {subj_text}")
        if obj_wiki_id is None:
            issues.append(f"Object not linked: {obj_text}")
        
        # Check type constraints
        constraints = RELATION_CONSTRAINTS.get(predicate, {})
        
        # Check if relation already exists
        if subj_wiki_id and obj_wiki_id:
            existing = self.kg.find_relation(subj_wiki_id, predicate, obj_wiki_id)
            if existing:
                status = "duplicate"
                matched_existing = existing
                return ValidationResult(
                    item_type="relation",
                    item_id=f"{subj_text}-{predicate}-{obj_text}",
                    status=status,
                    confidence=confidence,
                    matched_existing=matched_existing,
                )
        
        # Check for conflicts
        # e.g., if BORN_IN is unique and entity already has a birthplace
        if constraints.get("unique") and subj_wiki_id:
            # Check if subject already has this relation type
            for existing_rel in self.kg.relations.get(predicate, []):
                if existing_rel.get("source_wiki_id") == subj_wiki_id:
                    status = "conflict"
                    issues.append(f"Conflicts with existing {predicate}")
                    matched_existing = existing_rel
                    break
        
        # Validate predicate
        if not predicate:
            issues.append("Missing predicate")
            status = "invalid"
        
        # Check confidence
        if confidence < 0.5:
            issues.append(f"Low confidence: {confidence:.2f}")
        
        return ValidationResult(
            item_type="relation",
            item_id=f"{subj_text}-{predicate}-{obj_text}",
            status=status,
            confidence=confidence,
            issues=issues,
            matched_existing=matched_existing,
        )
    
    def validate_entities_file(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
    ) -> ValidationReport:
        """
        Validate all entities in a file.
        
        Args:
            input_file: Input JSONL file with recognized entities
            output_file: Output file for validated entities
            
        Returns:
            ValidationReport
        """
        report = ValidationReport()
        validated_records = []
        
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, total=total_lines, desc="Validating entities"):
                try:
                    record = json.loads(line)
                    entities = record.get("entities", [])
                    
                    validated_entities = []
                    for entity in entities:
                        result = self.validate_entity(entity)
                        report.total_entities += 1
                        
                        # Update confidence distribution
                        if result.confidence >= 0.85:
                            report.high_confidence += 1
                        elif result.confidence >= 0.70:
                            report.medium_confidence += 1
                        else:
                            report.low_confidence += 1
                        
                        # Update status counts
                        if result.status == "duplicate":
                            report.duplicate_entities += 1
                        elif result.status == "new_candidate":
                            report.new_entities += 1
                        elif result.status == "invalid":
                            report.invalid_entities += 1
                        else:
                            report.valid_entities += 1
                        
                        # Add issues to report
                        if result.issues:
                            report.issues.append(result.to_dict())
                        
                        # Add validation result to entity
                        entity["validation"] = {
                            "status": result.status,
                            "matched_existing": result.matched_existing,
                            "issues": result.issues,
                        }
                        validated_entities.append(entity)
                    
                    record["entities"] = validated_entities
                    validated_records.append(record)
                    
                except json.JSONDecodeError:
                    continue
        
        # Write validated output
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                for record in validated_records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        return report
    
    def validate_relations_file(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
    ) -> ValidationReport:
        """
        Validate all relations in a file.
        
        Args:
            input_file: Input JSONL file with extracted relations
            output_file: Output file for validated relations
            
        Returns:
            ValidationReport
        """
        report = ValidationReport()
        validated_records = []
        
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, total=total_lines, desc="Validating relations"):
                try:
                    record = json.loads(line)
                    relations = record.get("relations", [])
                    
                    validated_relations = []
                    for relation in relations:
                        result = self.validate_relation(relation)
                        report.total_relations += 1
                        
                        # Update confidence distribution
                        if result.confidence >= 0.85:
                            report.high_confidence += 1
                        elif result.confidence >= 0.70:
                            report.medium_confidence += 1
                        else:
                            report.low_confidence += 1
                        
                        # Update status counts
                        if result.status == "duplicate":
                            report.duplicate_relations += 1
                        elif result.status == "conflict":
                            report.conflict_relations += 1
                        elif result.status == "invalid":
                            report.invalid_relations += 1
                        elif result.status == "valid":
                            report.new_relations += 1
                            report.valid_relations += 1
                        
                        # Add issues to report
                        if result.issues:
                            report.issues.append(result.to_dict())
                        
                        # Add validation result to relation
                        relation["validation"] = {
                            "status": result.status,
                            "matched_existing": result.matched_existing,
                            "issues": result.issues,
                        }
                        validated_relations.append(relation)
                    
                    record["relations"] = validated_relations
                    validated_records.append(record)
                    
                except json.JSONDecodeError:
                    continue
        
        # Write validated output
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                for record in validated_records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        return report
    
    def generate_report(
        self,
        entity_report: ValidationReport,
        relation_report: ValidationReport,
        output_file: Optional[Path] = None,
    ) -> Dict:
        """
        Generate combined validation report.
        
        Args:
            entity_report: Report from entity validation
            relation_report: Report from relation validation
            output_file: Optional output file path
            
        Returns:
            Combined report dict
        """
        combined = {
            "entities": entity_report.to_dict(),
            "relations": relation_report.to_dict(),
            "summary": {
                "total_items": entity_report.total_entities + relation_report.total_relations,
                "ready_for_import": entity_report.new_entities + relation_report.new_relations,
                "duplicates": entity_report.duplicate_entities + relation_report.duplicate_relations,
                "conflicts": relation_report.conflict_relations,
                "issues_found": len(entity_report.issues) + len(relation_report.issues),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(combined, f, ensure_ascii=False, indent=2)
            logger.info(f"Report saved to {output_file}")
        
        return combined


def main():
    """CLI entry point for validation."""
    parser = argparse.ArgumentParser(
        description="Validate enrichment data for Vietnam Football KG"
    )
    
    parser.add_argument(
        "--validate-entities",
        action="store_true",
        help="Validate recognized entities",
    )
    parser.add_argument(
        "--validate-relations",
        action="store_true",
        help="Validate extracted relations",
    )
    parser.add_argument(
        "--validate-all",
        action="store_true",
        help="Validate both entities and relations",
    )
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate validation report",
    )
    parser.add_argument(
        "--entities-file",
        type=str,
        help="Input file for entities",
    )
    parser.add_argument(
        "--relations-file",
        type=str,
        help="Input file for relations",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for validated files",
    )
    
    args = parser.parse_args()
    
    validator = EnrichmentValidator()
    
    entities_file = Path(args.entities_file) if args.entities_file else ENRICHMENT_DIR / "recognized_entities.jsonl"
    relations_file = Path(args.relations_file) if args.relations_file else ENRICHMENT_DIR / "extracted_relations.jsonl"
    output_dir = Path(args.output_dir) if args.output_dir else ENRICHMENT_DIR
    
    entity_report = ValidationReport()
    relation_report = ValidationReport()
    
    if args.validate_entities or args.validate_all:
        if entities_file.exists():
            print(f"\n=== Validating Entities ===")
            print(f"Input: {entities_file}")
            entity_report = validator.validate_entities_file(
                entities_file,
                output_dir / "validated_entities.jsonl"
            )
            print(f"\nEntity Validation Results:")
            print(f"  Total: {entity_report.total_entities}")
            print(f"  Duplicates: {entity_report.duplicate_entities}")
            print(f"  New candidates: {entity_report.new_entities}")
            print(f"  Invalid: {entity_report.invalid_entities}")
        else:
            print(f"Entities file not found: {entities_file}")
    
    if args.validate_relations or args.validate_all:
        if relations_file.exists():
            print(f"\n=== Validating Relations ===")
            print(f"Input: {relations_file}")
            relation_report = validator.validate_relations_file(
                relations_file,
                output_dir / "validated_relations.jsonl"
            )
            print(f"\nRelation Validation Results:")
            print(f"  Total: {relation_report.total_relations}")
            print(f"  Duplicates: {relation_report.duplicate_relations}")
            print(f"  New: {relation_report.new_relations}")
            print(f"  Conflicts: {relation_report.conflict_relations}")
            print(f"  Invalid: {relation_report.invalid_relations}")
        else:
            print(f"Relations file not found: {relations_file}")
    
    if args.generate_report or args.validate_all:
        print(f"\n=== Generating Report ===")
        report = validator.generate_report(
            entity_report,
            relation_report,
            REPORTS_DIR / "enrichment_validation_report.json"
        )
        print(f"Report saved to {REPORTS_DIR / 'enrichment_validation_report.json'}")
        print(f"\nSummary:")
        print(f"  Total items: {report['summary']['total_items']}")
        print(f"  Ready for import: {report['summary']['ready_for_import']}")
        print(f"  Duplicates: {report['summary']['duplicates']}")
        print(f"  Conflicts: {report['summary']['conflicts']}")
    
    if not any([args.validate_entities, args.validate_relations, args.validate_all, args.generate_report]):
        parser.print_help()


if __name__ == "__main__":
    main()
