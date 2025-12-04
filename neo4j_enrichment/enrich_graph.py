"""
Graph Enricher for Vietnam Football Knowledge Graph

This module imports validated enrichment data into Neo4j:
- Creates new nodes with source tagging
- Creates new relationships with confidence scores
- Handles conflicts and deduplication
- Supports dry-run mode for preview

Usage:
    python -m neo4j_enrichment.enrich_graph --dry-run
    python -m neo4j_enrichment.enrich_graph --import-all --confidence-threshold 0.75
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
from typing import Any, Dict, List, Optional, Set, Tuple

from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    BASE_DIR,
    DATA_DIR,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    REPORTS_DIR,
)

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

# Entity type to Neo4j label mapping
# Note: Position is NOT a node - it's a property of Player
# Note: Date/Event entities are skipped (not useful as nodes)
ENTITY_TYPE_TO_LABEL = {
    "PLAYER": "Player",
    "COACH": "Coach",
    "CLUB": "Club",
    "NATIONAL_TEAM": "NationalTeam",
    "STADIUM": "Stadium",
    "PROVINCE": "Province",
    "COMPETITION": "Competition",
}

# Entity types to SKIP (not create as nodes)
SKIP_ENTITY_TYPES = {
    "POSITION",  # Position is a property of Player, not a separate node
    "DATE",      # Dates are not useful as nodes
    "EVENT",     # Events are usually competitions or matches
    "Entity",    # Generic unclassified entities
}

# Blacklist patterns for entity text (regex patterns)
ENTITY_TEXT_BLACKLIST = [
    r"^##",              # Tokenization artifacts
    r"^[A-Z]{2,4}$",     # Short acronyms like "VFF", "AFC" (organizations, not clubs)
    r"(?i)^(báo|tạp chí|liên đoàn|hiệp hội|sở|ủy ban|tiểu ban|công ty|tập đoàn)",  # Organizations
    r"(?i)(federation|association|committee|newspaper|magazine)$",
    r"^\d+$",            # Pure numbers
    r"^[A-Za-z]$",       # Single letters
]

# Minimum confidence by entity type (stricter for model-generated)
MIN_CONFIDENCE_BY_TYPE = {
    "PLAYER": 0.85,      # Players need high confidence
    "COACH": 0.85,
    "CLUB": 0.90,        # Clubs are often misidentified
    "NATIONAL_TEAM": 0.80,
    "STADIUM": 0.80,
    "PROVINCE": 0.95,    # Provinces should be from dictionary
    "COMPETITION": 0.85,
}

# Minimum text length by entity type
MIN_TEXT_LENGTH_BY_TYPE = {
    "PLAYER": 4,         # Vietnamese names at least 4 chars
    "COACH": 4,
    "CLUB": 5,
    "NATIONAL_TEAM": 5,
    "STADIUM": 5,
    "PROVINCE": 3,
    "COMPETITION": 5,
}

# Only accept from these sources (strict mode)
TRUSTED_SOURCES = {"dictionary"}  # Only dictionary matches are trusted for new entities

# New relation types to be added by enrichment
NEW_RELATION_TYPES = [
    "SCORED_IN",
    "DEFEATED",
    "TRANSFERRED_TO",
    "CAPTAINED",
    "WON_AWARD",
    "COMPETED_WITH",
]


def is_valid_entity_for_import(entity: Dict, strict_mode: bool = True) -> bool:
    """
    Validate if an entity should be imported to Neo4j.
    
    Args:
        entity: Entity dict with type, text, confidence, source
        strict_mode: If True, only accept dictionary matches
        
    Returns:
        True if entity is valid for import
    """
    entity_type = entity.get("type", "")
    text = entity.get("text", "").strip()
    confidence = entity.get("confidence", 0.0)
    source = entity.get("source", "unknown")
    validation = entity.get("validation", {})
    status = validation.get("status", "unknown")
    
    # Skip if already exists (duplicate)
    if status == "duplicate":
        return False
    
    # Skip blacklisted entity types
    if entity_type in SKIP_ENTITY_TYPES:
        return False
    
    # Skip if type not in allowed list
    if entity_type not in ENTITY_TYPE_TO_LABEL:
        return False
    
    # Check minimum text length
    min_length = MIN_TEXT_LENGTH_BY_TYPE.get(entity_type, 3)
    if len(text) < min_length:
        return False
    
    # Check blacklist patterns
    for pattern in ENTITY_TEXT_BLACKLIST:
        if re.search(pattern, text):
            return False
    
    # Check minimum confidence by type
    min_conf = MIN_CONFIDENCE_BY_TYPE.get(entity_type, 0.75)
    if confidence < min_conf:
        return False
    
    # Strict mode: only accept dictionary matches for new entities
    if strict_mode and status == "new_candidate":
        if source not in TRUSTED_SOURCES:
            return False
    
    return True


@dataclass
class ImportResult:
    """Result of import operation."""
    nodes_created: int = 0
    nodes_updated: int = 0
    edges_created: int = 0
    edges_updated: int = 0
    conflicts: List[Dict] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "nodes_created": self.nodes_created,
            "nodes_updated": self.nodes_updated,
            "edges_created": self.edges_created,
            "edges_updated": self.edges_updated,
            "conflicts": len(self.conflicts),
            "errors": len(self.errors),
        }


class Neo4jConnection:
    """
    Neo4j database connection handler.
    """
    
    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j URI
            user: Username
            password: Password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
    
    def connect(self) -> bool:
        """
        Establish connection to Neo4j.
        
        Returns:
            True if successful
        """
        try:
            from neo4j import GraphDatabase
            
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            logger.info("Connected to Neo4j successfully")
            return True
            
        except ImportError:
            logger.error("neo4j package not installed. Install with: pip install neo4j")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self) -> None:
        """Close the connection."""
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def execute(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dicts
        """
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    
    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> Dict:
        """
        Execute a write query and return summary.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query summary dict
        """
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }


class GraphEnricher:
    """
    Main class for enriching the knowledge graph with extracted data.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.75,
        dry_run: bool = True,
    ):
        """
        Initialize the graph enricher.
        
        Args:
            confidence_threshold: Minimum confidence for import
            dry_run: If True, only preview changes without committing
        """
        self.confidence_threshold = confidence_threshold
        self.dry_run = dry_run
        
        self.connection = Neo4jConnection()
        self._connected = False
        
        # Track changes for reporting
        self.pending_nodes: List[Dict] = []
        self.pending_edges: List[Dict] = []
        
        # Ensure directories exist
        ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> bool:
        """Connect to Neo4j."""
        if self.dry_run:
            logger.info("Dry run mode - no database connection needed")
            return True
        
        self._connected = self.connection.connect()
        return self._connected
    
    def close(self) -> None:
        """Close connection."""
        if self._connected:
            self.connection.close()
            self._connected = False
    
    def _generate_node_cypher(
        self,
        entity: Dict,
        source: str = "text_extraction",
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Generate Cypher query for creating/merging a node.
        
        Args:
            entity: Entity dict
            source: Source tag
            
        Returns:
            Tuple of (cypher query, parameters) or (None, None) if entity should be skipped
        """
        entity_type = entity.get("type", "Entity")
        
        # Skip entity types that shouldn't become nodes
        if entity_type in SKIP_ENTITY_TYPES:
            return None, None
            
        label = ENTITY_TYPE_TO_LABEL.get(entity_type)
        if not label:
            # Unknown entity type, skip it
            return None, None
        
        text = entity.get("text", "")
        wiki_id = entity.get("wiki_id")
        confidence = entity.get("confidence", 0.0)
        
        if wiki_id:
            # Merge on wiki_id
            query = f"""
            MERGE (n:{label} {{wiki_id: $wiki_id}})
            ON CREATE SET 
                n.name = $name,
                n.source = $source,
                n.confidence = $confidence,
                n.created_at = datetime(),
                n.created_by = 'enrichment'
            ON MATCH SET
                n.enriched_at = datetime(),
                n.enrichment_source = $source,
                n.enrichment_confidence = $confidence
            RETURN n
            """
            params = {
                "wiki_id": wiki_id,
                "name": text,
                "source": source,
                "confidence": confidence,
            }
        else:
            # Create new node (candidate)
            query = f"""
            CREATE (n:{label} {{
                name: $name,
                source: $source,
                confidence: $confidence,
                is_candidate: true,
                created_at: datetime(),
                created_by: 'enrichment'
            }})
            RETURN n
            """
            params = {
                "name": text,
                "source": source,
                "confidence": confidence,
            }
        
        return (query, params)
    
    def _generate_edge_cypher(
        self,
        relation: Dict,
        source: str = "text_extraction",
    ) -> Tuple[str, Dict]:
        """
        Generate Cypher query for creating/merging a relationship.
        
        Args:
            relation: Relation dict
            source: Source tag
            
        Returns:
            Tuple of (cypher query, parameters)
        """
        subject = relation.get("subject", {})
        predicate = relation.get("predicate", "RELATED_TO")
        obj = relation.get("object", {})
        confidence = relation.get("confidence", 0.0)
        context = relation.get("context", "")
        
        subj_wiki_id = subject.get("wiki_id")
        obj_wiki_id = obj.get("wiki_id")
        
        subj_type = subject.get("type", "Entity")
        obj_type = obj.get("type", "Entity")
        
        subj_label = ENTITY_TYPE_TO_LABEL.get(subj_type, "Entity")
        obj_label = ENTITY_TYPE_TO_LABEL.get(obj_type, "Entity")
        
        # Build match clause
        if subj_wiki_id and obj_wiki_id:
            # Both entities have wiki_ids - use them for matching
            query = f"""
            MATCH (a:{subj_label} {{wiki_id: $subj_wiki_id}})
            MATCH (b:{obj_label} {{wiki_id: $obj_wiki_id}})
            MERGE (a)-[r:{predicate}]->(b)
            ON CREATE SET
                r.source = $source,
                r.confidence = $confidence,
                r.context = $context,
                r.created_at = datetime()
            ON MATCH SET
                r.enriched_at = datetime(),
                r.enrichment_confidence = $confidence
            RETURN r
            """
            params = {
                "subj_wiki_id": subj_wiki_id,
                "obj_wiki_id": obj_wiki_id,
                "source": source,
                "confidence": confidence,
                "context": context,
            }
        else:
            # Try matching by name (less reliable)
            subj_name = subject.get("text", "")
            obj_name = obj.get("text", "")
            
            query = f"""
            MATCH (a:{subj_label}) WHERE toLower(a.name) CONTAINS toLower($subj_name)
            MATCH (b:{obj_label}) WHERE toLower(b.name) CONTAINS toLower($obj_name)
            MERGE (a)-[r:{predicate}]->(b)
            ON CREATE SET
                r.source = $source,
                r.confidence = $confidence,
                r.context = $context,
                r.matched_by_name = true,
                r.created_at = datetime()
            RETURN r
            """
            params = {
                "subj_name": subj_name,
                "obj_name": obj_name,
                "source": source,
                "confidence": confidence,
                "context": context,
            }
        
        return (query, params)
    
    def process_validated_entities(
        self,
        input_file: Path,
    ) -> ImportResult:
        """
        Process validated entities file and prepare for import.
        
        Args:
            input_file: Path to validated entities JSONL
            
        Returns:
            ImportResult
        """
        result = ImportResult()
        
        if not input_file.exists():
            logger.warning(f"Input file not found: {input_file}")
            return result
        
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        skipped_count = 0
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, total=total_lines, desc="Processing entities"):
                try:
                    record = json.loads(line)
                    entities = record.get("entities", [])
                    
                    for entity in entities:
                        # Use strict validation
                        if not is_valid_entity_for_import(entity, strict_mode=True):
                            skipped_count += 1
                            continue
                        
                        # Generate Cypher (may return None if entity type should be skipped)
                        query, params = self._generate_node_cypher(entity)
                        
                        # Skip if entity type is not allowed
                        if query is None:
                            skipped_count += 1
                            continue
                        
                        self.pending_nodes.append({
                            "query": query,
                            "params": params,
                            "entity": entity,
                        })
                        
                        validation = entity.get("validation", {})
                        status = validation.get("status", "unknown")
                        if status == "new_candidate":
                            result.nodes_created += 1
                        else:
                            result.nodes_updated += 1
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    result.errors.append({"error": str(e)})
        
        logger.info(f"Skipped {skipped_count} entities due to strict validation")
        return result
    
    def process_validated_relations(
        self,
        input_file: Path,
    ) -> ImportResult:
        """
        Process validated relations file and prepare for import.
        
        Args:
            input_file: Path to validated relations JSONL
            
        Returns:
            ImportResult
        """
        result = ImportResult()
        
        if not input_file.exists():
            logger.warning(f"Input file not found: {input_file}")
            return result
        
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8'))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, total=total_lines, desc="Processing relations"):
                try:
                    record = json.loads(line)
                    relations = record.get("relations", [])
                    
                    for relation in relations:
                        confidence = relation.get("confidence", 0.0)
                        validation = relation.get("validation", {})
                        status = validation.get("status", "unknown")
                        
                        # Skip low confidence
                        if confidence < self.confidence_threshold:
                            continue
                        
                        # Skip duplicates
                        if status == "duplicate":
                            continue
                        
                        # Handle conflicts
                        if status == "conflict":
                            result.conflicts.append(relation)
                            continue
                        
                        # Generate Cypher
                        query, params = self._generate_edge_cypher(relation)
                        
                        self.pending_edges.append({
                            "query": query,
                            "params": params,
                            "relation": relation,
                        })
                        
                        result.edges_created += 1
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    result.errors.append({"error": str(e)})
        
        return result
    
    def preview_changes(self) -> Dict:
        """
        Preview pending changes without executing.
        
        Returns:
            Summary of pending changes
        """
        return {
            "pending_nodes": len(self.pending_nodes),
            "pending_edges": len(self.pending_edges),
            "sample_node_queries": [
                {
                    "entity": p["entity"].get("text"),
                    "type": p["entity"].get("type"),
                }
                for p in self.pending_nodes[:5]
            ],
            "sample_edge_queries": [
                {
                    "subject": p["relation"]["subject"].get("text"),
                    "predicate": p["relation"].get("predicate"),
                    "object": p["relation"]["object"].get("text"),
                }
                for p in self.pending_edges[:5]
            ],
        }
    
    def execute_import(self) -> ImportResult:
        """
        Execute all pending imports.
        
        Returns:
            ImportResult with actual counts
        """
        result = ImportResult()
        
        if self.dry_run:
            logger.info("Dry run mode - skipping actual import")
            result.nodes_created = len(self.pending_nodes)
            result.edges_created = len(self.pending_edges)
            return result
        
        if not self._connected:
            logger.error("Not connected to Neo4j")
            return result
        
        # Execute node imports
        logger.info(f"Importing {len(self.pending_nodes)} nodes...")
        for item in tqdm(self.pending_nodes, desc="Importing nodes"):
            try:
                summary = self.connection.execute_write(
                    item["query"],
                    item["params"]
                )
                result.nodes_created += summary.get("nodes_created", 0)
            except Exception as e:
                result.errors.append({
                    "type": "node",
                    "entity": item["entity"].get("text"),
                    "error": str(e),
                })
        
        # Execute edge imports
        logger.info(f"Importing {len(self.pending_edges)} edges...")
        for item in tqdm(self.pending_edges, desc="Importing edges"):
            try:
                summary = self.connection.execute_write(
                    item["query"],
                    item["params"]
                )
                result.edges_created += summary.get("relationships_created", 0)
            except Exception as e:
                result.errors.append({
                    "type": "edge",
                    "relation": f"{item['relation']['subject'].get('text')} -> {item['relation']['object'].get('text')}",
                    "error": str(e),
                })
        
        return result
    
    def generate_cypher_scripts(
        self,
        output_dir: Optional[Path] = None,
    ) -> None:
        """
        Generate Cypher scripts for manual import.
        
        Args:
            output_dir: Output directory for scripts
        """
        if output_dir is None:
            output_dir = BASE_DIR / "neo4j_enrichment"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate node import script
        node_script = output_dir / "import_enriched_nodes.cypher"
        with open(node_script, 'w', encoding='utf-8') as f:
            f.write("// Enriched nodes import script\n")
            f.write(f"// Generated: {datetime.utcnow().isoformat()}\n")
            f.write(f"// Total nodes: {len(self.pending_nodes)}\n\n")
            
            for item in self.pending_nodes:
                # Format query with parameters inline
                query = item["query"]
                params = item["params"]
                
                # Simple parameter substitution for preview
                for key, value in params.items():
                    if isinstance(value, str):
                        query = query.replace(f"${key}", f"'{value}'")
                    elif value is None:
                        query = query.replace(f"${key}", "null")
                    else:
                        query = query.replace(f"${key}", str(value))
                
                f.write(query + ";\n\n")
        
        logger.info(f"Node import script saved to {node_script}")
        
        # Generate edge import script
        edge_script = output_dir / "import_enriched_edges.cypher"
        with open(edge_script, 'w', encoding='utf-8') as f:
            f.write("// Enriched edges import script\n")
            f.write(f"// Generated: {datetime.utcnow().isoformat()}\n")
            f.write(f"// Total edges: {len(self.pending_edges)}\n\n")
            
            for item in self.pending_edges:
                query = item["query"]
                params = item["params"]
                
                for key, value in params.items():
                    if isinstance(value, str):
                        query = query.replace(f"${key}", f"'{value}'")
                    elif value is None:
                        query = query.replace(f"${key}", "null")
                    else:
                        query = query.replace(f"${key}", str(value))
                
                f.write(query + ";\n\n")
        
        logger.info(f"Edge import script saved to {edge_script}")
    
    def generate_report(
        self,
        result: ImportResult,
        output_file: Optional[Path] = None,
    ) -> Dict:
        """
        Generate import report.
        
        Args:
            result: ImportResult from import
            output_file: Optional output file path
            
        Returns:
            Report dict
        """
        report = {
            "import_summary": result.to_dict(),
            "dry_run": self.dry_run,
            "confidence_threshold": self.confidence_threshold,
            "pending_changes": {
                "nodes": len(self.pending_nodes),
                "edges": len(self.pending_edges),
            },
            "conflicts": result.conflicts[:10],  # First 10 conflicts
            "errors": result.errors[:10],  # First 10 errors
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"Report saved to {output_file}")
        
        return report


def generate_schema_update_cypher() -> str:
    """
    Generate Cypher for schema updates (new indexes, constraints).
    
    Returns:
        Cypher script string
    """
    script = """
// =============================================================================
// Schema updates for enrichment
// Generated: {timestamp}
// =============================================================================

// Create indexes for enrichment tracking
CREATE INDEX enrichment_source IF NOT EXISTS FOR (n:Player) ON (n.source);
CREATE INDEX enrichment_source IF NOT EXISTS FOR (n:Coach) ON (n.source);
CREATE INDEX enrichment_source IF NOT EXISTS FOR (n:Club) ON (n.source);

// Create indexes for candidate entities
CREATE INDEX is_candidate IF NOT EXISTS FOR (n:Player) ON (n.is_candidate);
CREATE INDEX is_candidate IF NOT EXISTS FOR (n:Coach) ON (n.is_candidate);
CREATE INDEX is_candidate IF NOT EXISTS FOR (n:Club) ON (n.is_candidate);

// New node labels for enrichment
CREATE CONSTRAINT event_id IF NOT EXISTS FOR (n:Event) REQUIRE n.event_id IS UNIQUE;

// =============================================================================
// New relationship types documentation
// =============================================================================
// SCORED_IN: (Player)-[:SCORED_IN]->(Event/Competition)
// DEFEATED: (Team)-[:DEFEATED]->(Team)
// TRANSFERRED_TO: (Player)-[:TRANSFERRED_TO]->(Club)
// CAPTAINED: (Player)-[:CAPTAINED]->(Team)
// WON_AWARD: (Person)-[:WON_AWARD]->(Event)
// COMPETED_WITH: (Team)-[:COMPETED_WITH]->(Team)

""".format(timestamp=datetime.utcnow().isoformat())
    
    return script


def main():
    """CLI entry point for graph enricher."""
    parser = argparse.ArgumentParser(
        description="Import enriched data into Neo4j"
    )
    
    parser.add_argument(
        "--import-all",
        action="store_true",
        help="Import all validated entities and relations",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without committing (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the import (disables dry-run)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.75,
        help="Minimum confidence for import (default: 0.75)",
    )
    parser.add_argument(
        "--entities-file",
        type=str,
        help="Validated entities file",
    )
    parser.add_argument(
        "--relations-file",
        type=str,
        help="Validated relations file",
    )
    parser.add_argument(
        "--generate-scripts",
        action="store_true",
        help="Generate Cypher scripts for manual import",
    )
    parser.add_argument(
        "--generate-schema",
        action="store_true",
        help="Generate schema update script",
    )
    
    args = parser.parse_args()
    
    # Handle dry-run vs execute
    dry_run = not args.execute
    
    if args.generate_schema:
        print("\n=== Schema Update Script ===")
        script = generate_schema_update_cypher()
        print(script)
        
        # Save to file
        output_file = BASE_DIR / "neo4j_enrichment" / "schema_enrichment.cypher"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script)
        print(f"\nSaved to {output_file}")
        return
    
    # Initialize enricher
    enricher = GraphEnricher(
        confidence_threshold=args.confidence_threshold,
        dry_run=dry_run,
    )
    
    entities_file = Path(args.entities_file) if args.entities_file else ENRICHMENT_DIR / "validated_entities.jsonl"
    relations_file = Path(args.relations_file) if args.relations_file else ENRICHMENT_DIR / "validated_relations.jsonl"
    
    if args.import_all:
        print(f"\n=== Graph Enrichment ===")
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"Confidence threshold: {args.confidence_threshold}")
        
        # Connect if not dry run
        if not enricher.connect():
            print("Failed to connect to Neo4j")
            return
        
        try:
            # Process entities
            if entities_file.exists():
                print(f"\nProcessing entities: {entities_file}")
                entity_result = enricher.process_validated_entities(entities_file)
                print(f"  Nodes to create: {entity_result.nodes_created}")
                print(f"  Nodes to update: {entity_result.nodes_updated}")
            
            # Process relations
            if relations_file.exists():
                print(f"\nProcessing relations: {relations_file}")
                relation_result = enricher.process_validated_relations(relations_file)
                print(f"  Edges to create: {relation_result.edges_created}")
                print(f"  Conflicts: {len(relation_result.conflicts)}")
            
            # Preview
            preview = enricher.preview_changes()
            print(f"\n=== Preview ===")
            print(f"Pending nodes: {preview['pending_nodes']}")
            print(f"Pending edges: {preview['pending_edges']}")
            
            if preview['sample_node_queries']:
                print("\nSample nodes:")
                for sample in preview['sample_node_queries']:
                    print(f"  [{sample['type']}] {sample['entity']}")
            
            if preview['sample_edge_queries']:
                print("\nSample edges:")
                for sample in preview['sample_edge_queries']:
                    print(f"  ({sample['subject']}) --[{sample['predicate']}]--> ({sample['object']})")
            
            # Generate scripts if requested
            if args.generate_scripts:
                enricher.generate_cypher_scripts()
            
            # Execute if not dry run
            if not dry_run:
                print("\n=== Executing Import ===")
                result = enricher.execute_import()
                print(f"Nodes created: {result.nodes_created}")
                print(f"Edges created: {result.edges_created}")
                print(f"Errors: {len(result.errors)}")
            
            # Generate report
            combined_result = ImportResult(
                nodes_created=entity_result.nodes_created if entities_file.exists() else 0,
                edges_created=relation_result.edges_created if relations_file.exists() else 0,
            )
            report = enricher.generate_report(
                combined_result,
                REPORTS_DIR / "enrichment_import_report.json"
            )
            
        finally:
            enricher.close()
        
        return
    
    if args.generate_scripts:
        print("\n=== Generating Cypher Scripts ===")
        
        # Load and process files first
        if entities_file.exists():
            enricher.process_validated_entities(entities_file)
        if relations_file.exists():
            enricher.process_validated_relations(relations_file)
        
        enricher.generate_cypher_scripts()
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
