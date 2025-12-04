"""
Import Matched Relations to Neo4j

This script imports relations extracted from matched entities.
These relations are SAFE because:
1. Both subject and object exist in database (have wiki_id)
2. Extracted using strict co-occurrence patterns
3. High confidence (>= 0.7)

Usage:
    python -m neo4j_enrichment.import_matched_relations --dry-run
    python -m neo4j_enrichment.import_matched_relations --execute
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

try:
    from neo4j import GraphDatabase
except ImportError:
    print("Please install neo4j: pip install neo4j")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ENRICHMENT_DIR = DATA_DIR / "enrichment"
REPORTS_DIR = BASE_DIR / "reports"

# Relation type mapping to Neo4j
RELATION_TYPE_MAP = {
    "PLAYED_FOR": "PLAYED_FOR",
    "PLAYED_FOR_NATIONAL": "PLAYED_FOR_NATIONAL",
    "COMPETED_IN": "COMPETED_IN",
    "COMPETES_IN": "COMPETES_IN",
    "COACHED": "COACHED",
    "COACHED_NATIONAL": "COACHED_NATIONAL",
    "DEFEATED": "DEFEATED",
    "TRANSFERRED_TO": "TRANSFERRED_TO",
}


@dataclass
class ImportStats:
    """Import statistics."""
    total: int = 0
    created: int = 0
    skipped_exists: int = 0
    skipped_no_match: int = 0
    errors: int = 0


class MatchedRelationImporter:
    """Import matched relations to Neo4j."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.stats = ImportStats()
        self._connected = False
        
    def connect(self) -> bool:
        """Test connection."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            self._connected = True
            logger.info("Connected to Neo4j successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def close(self):
        """Close connection."""
        if self.driver:
            self.driver.close()
    
    def _find_node_by_wiki_id(self, wiki_id: int, entity_type: str) -> Optional[dict]:
        """Find node by wiki_id."""
        # Map entity type to Neo4j labels
        label_map = {
            "PLAYER": "Player",
            "COACH": "Coach", 
            "CLUB": "Club",
            "COMPETITION": "Competition",
            "STADIUM": "Stadium",
            "NATIONAL_TEAM": "NationalTeam",
            "PROVINCE": "Province",
        }
        
        label = label_map.get(entity_type)
        if not label:
            return None
        
        query = f"""
        MATCH (n:{label} {{wiki_id: $wiki_id}})
        RETURN n.name as name, n.wiki_id as wiki_id
        LIMIT 1
        """
        
        with self.driver.session() as session:
            result = session.run(query, wiki_id=wiki_id)
            record = result.single()
            if record:
                return {"name": record["name"], "wiki_id": record["wiki_id"]}
        return None
    
    def _relation_exists(
        self,
        subj_wiki_id: int,
        subj_type: str,
        rel_type: str,
        obj_wiki_id: int,
        obj_type: str,
    ) -> bool:
        """Check if relation already exists."""
        label_map = {
            "PLAYER": "Player",
            "COACH": "Coach",
            "CLUB": "Club",
            "COMPETITION": "Competition",
            "STADIUM": "Stadium",
            "NATIONAL_TEAM": "NationalTeam",
            "PROVINCE": "Province",
        }
        
        subj_label = label_map.get(subj_type, "Entity")
        obj_label = label_map.get(obj_type, "Entity")
        neo4j_rel = RELATION_TYPE_MAP.get(rel_type, rel_type)
        
        query = f"""
        MATCH (s:{subj_label} {{wiki_id: $subj_wiki_id}})
              -[r:{neo4j_rel}]->
              (o:{obj_label} {{wiki_id: $obj_wiki_id}})
        RETURN count(r) as cnt
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                subj_wiki_id=subj_wiki_id,
                obj_wiki_id=obj_wiki_id,
            )
            record = result.single()
            return record["cnt"] > 0 if record else False
    
    def _create_relation(
        self,
        subj_wiki_id: int,
        subj_type: str,
        rel_type: str,
        obj_wiki_id: int,
        obj_type: str,
        confidence: float,
        context: str,
        pattern: str,
    ) -> bool:
        """Create a new relation."""
        label_map = {
            "PLAYER": "Player",
            "COACH": "Coach",
            "CLUB": "Club",
            "COMPETITION": "Competition",
            "STADIUM": "Stadium",
            "NATIONAL_TEAM": "NationalTeam",
            "PROVINCE": "Province",
        }
        
        subj_label = label_map.get(subj_type, "Entity")
        obj_label = label_map.get(obj_type, "Entity")
        neo4j_rel = RELATION_TYPE_MAP.get(rel_type, rel_type)
        
        query = f"""
        MATCH (s:{subj_label} {{wiki_id: $subj_wiki_id}})
        MATCH (o:{obj_label} {{wiki_id: $obj_wiki_id}})
        CREATE (s)-[r:{neo4j_rel} {{
            confidence: $confidence,
            context: $context,
            pattern: $pattern,
            source: 'enrichment',
            created_by: 'matched_relation_extractor',
            created_at: datetime()
        }}]->(o)
        RETURN r
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    subj_wiki_id=subj_wiki_id,
                    obj_wiki_id=obj_wiki_id,
                    confidence=confidence,
                    context=context[:500],  # Truncate context
                    pattern=pattern,
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"Error creating relation: {e}")
            return False
    
    def import_relations(
        self,
        input_file: Path,
        dry_run: bool = True,
        min_confidence: float = 0.7,
    ) -> ImportStats:
        """
        Import relations from JSONL file.
        
        Args:
            input_file: Path to matched_relations.jsonl
            dry_run: If True, don't actually create relations
            min_confidence: Minimum confidence threshold
            
        Returns:
            ImportStats
        """
        if not input_file.exists():
            logger.error(f"File not found: {input_file}")
            return self.stats
        
        relations = []
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    relations.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        logger.info(f"Loaded {len(relations)} relations")
        
        for rel in tqdm(relations, desc="Processing relations"):
            self.stats.total += 1
            
            subj = rel.get("subject", {})
            obj = rel.get("object", {})
            predicate = rel.get("predicate", "")
            confidence = rel.get("confidence", 0.0)
            context = rel.get("context", "")
            pattern = rel.get("pattern", "")
            
            # Skip low confidence
            if confidence < min_confidence:
                self.stats.skipped_no_match += 1
                continue
            
            subj_wiki_id = subj.get("wiki_id")
            obj_wiki_id = obj.get("wiki_id")
            
            # Need both wiki_ids
            if not subj_wiki_id or not obj_wiki_id:
                self.stats.skipped_no_match += 1
                continue
            
            subj_type = subj.get("type", "")
            obj_type = obj.get("type", "")
            
            if dry_run:
                # In dry-run, just count
                self.stats.created += 1
            else:
                # Check if relation already exists
                if self._relation_exists(
                    subj_wiki_id, subj_type, predicate, obj_wiki_id, obj_type
                ):
                    self.stats.skipped_exists += 1
                    continue
                
                # Create relation
                if self._create_relation(
                    subj_wiki_id, subj_type, predicate,
                    obj_wiki_id, obj_type,
                    confidence, context, pattern
                ):
                    self.stats.created += 1
                else:
                    self.stats.errors += 1
        
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="Import Matched Relations to Neo4j")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    parser.add_argument("--execute", action="store_true", help="Actually import to Neo4j")
    parser.add_argument("--min-confidence", type=float, default=0.7, help="Minimum confidence")
    parser.add_argument("--input", type=str, default=None, help="Input file path")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        args.dry_run = True  # Default to dry-run
    
    print("=" * 60)
    print("IMPORT MATCHED RELATIONS TO NEO4J")
    print("=" * 60)
    print(f"Mode: {'DRY-RUN (preview)' if args.dry_run else 'EXECUTE (import)'}")
    print(f"Min confidence: {args.min_confidence}")
    
    # Input file
    input_file = Path(args.input) if args.input else ENRICHMENT_DIR / "matched_relations.jsonl"
    print(f"Input: {input_file}")
    
    if not input_file.exists():
        print(f"ERROR: File not found: {input_file}")
        return
    
    # Create importer
    importer = MatchedRelationImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if not args.dry_run:
        if not importer.connect():
            print("ERROR: Could not connect to Neo4j")
            return
    
    # Import
    stats = importer.import_relations(
        input_file,
        dry_run=args.dry_run,
        min_confidence=args.min_confidence,
    )
    
    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total processed: {stats.total}")
    print(f"{'Would create' if args.dry_run else 'Created'}: {stats.created}")
    print(f"Skipped (already exists): {stats.skipped_exists}")
    print(f"Skipped (no match/low confidence): {stats.skipped_no_match}")
    print(f"Errors: {stats.errors}")
    
    if args.dry_run:
        print("\n" + "=" * 60)
        print("TO ACTUALLY IMPORT, RUN:")
        print("=" * 60)
        print("python -m neo4j_enrichment.import_matched_relations --execute")
    
    importer.close()


if __name__ == "__main__":
    main()
