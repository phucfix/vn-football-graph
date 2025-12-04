"""
Strict Enrichment Pipeline for Vietnam Football Knowledge Graph

This pipeline:
1. Reads extracted entities and relations
2. Applies STRICT validation (Vietnam-only, high confidence)
3. Separates into:
   - AUTO-IMPORT: Relations between existing entities (100% safe)
   - REVIEW-NEEDED: New entity candidates for human review
4. Exports review file and import file

Usage:
    python -m neo4j_enrichment.strict_pipeline --validate
    python -m neo4j_enrichment.strict_pipeline --export-review
    python -m neo4j_enrichment.strict_pipeline --import-safe
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import asdict

from tqdm import tqdm

from .strict_enrichment import (
    StrictEnrichmentConfig,
    StrictEnrichmentValidator,
    VietnamEntityValidator,
    ValidatedEntity,
    ValidatedRelation,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ENRICHMENT_DIR = DATA_DIR / "enrichment"
REPORTS_DIR = BASE_DIR / "reports"

# Output files
SAFE_RELATIONS_FILE = ENRICHMENT_DIR / "safe_relations.jsonl"  # Auto-import
REVIEW_ENTITIES_FILE = ENRICHMENT_DIR / "review_entities.jsonl"  # Human review
REVIEW_RELATIONS_FILE = ENRICHMENT_DIR / "review_relations.jsonl"  # Human review
STRICT_REPORT_FILE = REPORTS_DIR / "strict_enrichment_report.json"


class StrictEnrichmentPipeline:
    """Pipeline for strict enrichment with human review."""
    
    def __init__(self, config: StrictEnrichmentConfig = None):
        self.config = config or StrictEnrichmentConfig()
        self.validator = StrictEnrichmentValidator(self.config)
        
        # Results
        self.safe_relations: List[ValidatedRelation] = []
        self.review_entities: List[ValidatedEntity] = []
        self.review_relations: List[ValidatedRelation] = []
        
        # Stats
        self.stats = defaultdict(int)
    
    def process_entities(self, input_file: Path) -> None:
        """Process validated entities file with strict rules."""
        logger.info(f"Processing entities from {input_file}")
        
        if not input_file.exists():
            logger.warning(f"File not found: {input_file}")
            return
        
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, total=total_lines, desc="Processing entities"):
                try:
                    record = json.loads(line)
                    entities = record.get("entities", [])
                    sentence = record.get("sentence", "")
                    
                    for entity in entities:
                        self.stats["total_entities"] += 1
                        
                        # Apply strict validation
                        validated = self.validator.validate_entity(entity, sentence)
                        
                        if validated is None:
                            self.stats["rejected_entities"] += 1
                            continue
                        
                        if validated.is_new:
                            # New entity -> needs human review
                            self.review_entities.append(validated)
                            self.stats["review_entities"] += 1
                        else:
                            # Existing entity -> just stats
                            self.stats["matched_entities"] += 1
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing line: {e}")
        
        logger.info(f"Entities: {self.stats['total_entities']} total, "
                   f"{self.stats['matched_entities']} matched, "
                   f"{self.stats['review_entities']} need review, "
                   f"{self.stats['rejected_entities']} rejected")
    
    def process_relations(self, input_file: Path) -> None:
        """Process validated relations file with strict rules."""
        logger.info(f"Processing relations from {input_file}")
        
        if not input_file.exists():
            logger.warning(f"File not found: {input_file}")
            return
        
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, total=total_lines, desc="Processing relations"):
                try:
                    record = json.loads(line)
                    relations = record.get("relations", [])
                    sentence = record.get("sentence", "")
                    
                    for rel in relations:
                        self.stats["total_relations"] += 1
                        
                        subject = rel.get("subject", {})
                        predicate = rel.get("predicate", "RELATED_TO")
                        obj = rel.get("object", {})
                        confidence = rel.get("confidence", 0.0)
                        context = rel.get("context", sentence)
                        source = rel.get("source", "unknown")
                        
                        # Apply strict validation
                        validated = self.validator.validate_relation(
                            subject=subject,
                            predicate=predicate,
                            obj=obj,
                            confidence=confidence,
                            context=context,
                            source=source,
                        )
                        
                        if validated is None:
                            self.stats["rejected_relations"] += 1
                            continue
                        
                        # Check if both entities exist -> SAFE for auto-import
                        if not validated.subject.is_new and not validated.object.is_new:
                            self.safe_relations.append(validated)
                            self.stats["safe_relations"] += 1
                        else:
                            self.review_relations.append(validated)
                            self.stats["review_relations"] += 1
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing line: {e}")
        
        logger.info(f"Relations: {self.stats['total_relations']} total, "
                   f"{self.stats['safe_relations']} safe, "
                   f"{self.stats['review_relations']} need review, "
                   f"{self.stats['rejected_relations']} rejected")
    
    def export_safe_relations(self) -> Path:
        """Export relations that are safe for auto-import."""
        logger.info(f"Exporting {len(self.safe_relations)} safe relations")
        
        ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(SAFE_RELATIONS_FILE, 'w', encoding='utf-8') as f:
            for rel in self.safe_relations:
                data = {
                    "subject": {
                        "text": rel.subject.text,
                        "type": rel.subject.entity_type,
                        "wiki_id": rel.subject.wiki_id,
                        "matched_name": rel.subject.matched_existing.get("name") if rel.subject.matched_existing else None,
                    },
                    "predicate": rel.predicate,
                    "object": {
                        "text": rel.object.text,
                        "type": rel.object.entity_type,
                        "wiki_id": rel.object.wiki_id,
                        "matched_name": rel.object.matched_existing.get("name") if rel.object.matched_existing else None,
                    },
                    "confidence": rel.confidence,
                    "context": rel.context,
                    "source": rel.source,
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        logger.info(f"Saved to {SAFE_RELATIONS_FILE}")
        return SAFE_RELATIONS_FILE
    
    def export_review_candidates(self) -> Tuple[Path, Path]:
        """Export candidates that need human review."""
        ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Export entities for review
        logger.info(f"Exporting {len(self.review_entities)} entities for review")
        
        # Deduplicate by text+type
        seen = set()
        unique_entities = []
        for entity in self.review_entities:
            key = (entity.text.lower(), entity.entity_type)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        with open(REVIEW_ENTITIES_FILE, 'w', encoding='utf-8') as f:
            for entity in unique_entities:
                data = {
                    "text": entity.text,
                    "type": entity.entity_type,
                    "confidence": entity.confidence,
                    "source": entity.source,
                    "vietnam_related": entity.vietnam_related,
                    "notes": entity.validation_notes,
                    # Human review fields
                    "approved": None,  # True/False after review
                    "corrected_type": None,  # If type needs correction
                    "corrected_text": None,  # If text needs correction
                    "reject_reason": None,  # If rejected, why
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        logger.info(f"Saved {len(unique_entities)} unique entities to {REVIEW_ENTITIES_FILE}")
        
        # Export relations for review
        logger.info(f"Exporting {len(self.review_relations)} relations for review")
        
        with open(REVIEW_RELATIONS_FILE, 'w', encoding='utf-8') as f:
            for rel in self.review_relations:
                data = {
                    "subject": rel.subject.text,
                    "subject_type": rel.subject.entity_type,
                    "predicate": rel.predicate,
                    "object": rel.object.text,
                    "object_type": rel.object.entity_type,
                    "confidence": rel.confidence,
                    "context": rel.context,
                    # Human review fields
                    "approved": None,
                    "reject_reason": None,
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        logger.info(f"Saved to {REVIEW_RELATIONS_FILE}")
        
        return REVIEW_ENTITIES_FILE, REVIEW_RELATIONS_FILE
    
    def generate_report(self) -> Path:
        """Generate strict enrichment report."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "config": {
                "require_vietnam_context": self.config.require_vietnam_context,
                "min_confidence_dictionary": self.config.min_confidence_dictionary,
                "min_confidence_model": self.config.min_confidence_model,
                "require_both_entities_exist": self.config.require_both_entities_exist,
            },
            "statistics": dict(self.stats),
            "validator_stats": self.validator.get_stats(),
            "output_files": {
                "safe_relations": str(SAFE_RELATIONS_FILE),
                "review_entities": str(REVIEW_ENTITIES_FILE),
                "review_relations": str(REVIEW_RELATIONS_FILE),
            },
            "summary": {
                "safe_to_import": len(self.safe_relations),
                "entities_need_review": len(set((e.text.lower(), e.entity_type) for e in self.review_entities)),
                "relations_need_review": len(self.review_relations),
            },
        }
        
        with open(STRICT_REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Report saved to {STRICT_REPORT_FILE}")
        return STRICT_REPORT_FILE


def main():
    parser = argparse.ArgumentParser(description="Strict Enrichment Pipeline")
    parser.add_argument("--validate", action="store_true", help="Run strict validation")
    parser.add_argument("--export-review", action="store_true", help="Export candidates for review")
    parser.add_argument("--export-safe", action="store_true", help="Export safe relations")
    parser.add_argument("--full", action="store_true", help="Run full pipeline")
    
    args = parser.parse_args()
    
    if not any([args.validate, args.export_review, args.export_safe, args.full]):
        args.full = True  # Default to full pipeline
    
    print("=" * 60)
    print("STRICT ENRICHMENT PIPELINE")
    print("Vietnam Football Knowledge Graph")
    print("=" * 60)
    
    pipeline = StrictEnrichmentPipeline()
    
    # Input files
    entities_file = ENRICHMENT_DIR / "validated_entities.jsonl"
    relations_file = ENRICHMENT_DIR / "validated_relations.jsonl"
    
    if args.validate or args.full:
        print("\n[1/4] Processing entities with strict validation...")
        pipeline.process_entities(entities_file)
        
        print("\n[2/4] Processing relations with strict validation...")
        pipeline.process_relations(relations_file)
    
    if args.export_safe or args.full:
        print("\n[3/4] Exporting safe relations (auto-import ready)...")
        pipeline.export_safe_relations()
    
    if args.export_review or args.full:
        print("\n[4/4] Exporting candidates for human review...")
        pipeline.export_review_candidates()
    
    # Generate report
    print("\nGenerating report...")
    pipeline.generate_report()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Safe relations (auto-import): {len(pipeline.safe_relations)}")
    print(f"📝 Entities need review: {len(set((e.text.lower(), e.entity_type) for e in pipeline.review_entities))}")
    print(f"📝 Relations need review: {len(pipeline.review_relations)}")
    print(f"\nFiles created:")
    print(f"  - {SAFE_RELATIONS_FILE}")
    print(f"  - {REVIEW_ENTITIES_FILE}")
    print(f"  - {REVIEW_RELATIONS_FILE}")
    print(f"  - {STRICT_REPORT_FILE}")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Review entities in: data/enrichment/review_entities.jsonl")
    print("   - Set 'approved': true/false for each entity")
    print("2. Review relations in: data/enrichment/review_relations.jsonl")
    print("   - Set 'approved': true/false for each relation")
    print("3. Import safe relations: make import-safe-relations")
    print("4. Import reviewed data: make import-reviewed")


if __name__ == "__main__":
    main()
