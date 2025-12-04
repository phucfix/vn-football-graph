"""
Enrichment Analytics for Vietnam Football Knowledge Graph

This module provides analytics and visualization for the enrichment process:
- Pre/post enrichment statistics
- Quality metrics
- Confidence distribution analysis
- Growth tracking

Usage:
    python -m tools.enrichment_analytics --show-growth
    python -m tools.enrichment_analytics --compare-with-baseline
    python -m tools.enrichment_analytics --quality-metrics
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    BASE_DIR,
    DATA_DIR,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
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


@dataclass
class BaselineStats:
    """Statistics from the baseline (pre-enrichment) knowledge graph."""
    total_players: int = 0
    total_coaches: int = 0
    total_clubs: int = 0
    total_national_teams: int = 0
    total_stadiums: int = 0
    total_competitions: int = 0
    total_edges: int = 0
    edge_types: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "nodes": {
                "players": self.total_players,
                "coaches": self.total_coaches,
                "clubs": self.total_clubs,
                "national_teams": self.total_national_teams,
                "stadiums": self.total_stadiums,
                "competitions": self.total_competitions,
                "total": (self.total_players + self.total_coaches + 
                         self.total_clubs + self.total_national_teams +
                         self.total_stadiums + self.total_competitions),
            },
            "edges": {
                "total": self.total_edges,
                "by_type": self.edge_types,
            },
        }


@dataclass
class EnrichmentStats:
    """Statistics from the enrichment process."""
    entities_recognized: int = 0
    entities_new: int = 0
    entities_linked: int = 0
    entities_by_type: Dict[str, int] = field(default_factory=dict)
    
    relations_extracted: int = 0
    relations_new: int = 0
    relations_duplicate: int = 0
    relations_by_type: Dict[str, int] = field(default_factory=dict)
    
    confidence_distribution: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "entities": {
                "total_recognized": self.entities_recognized,
                "new_candidates": self.entities_new,
                "linked_to_existing": self.entities_linked,
                "by_type": self.entities_by_type,
            },
            "relations": {
                "total_extracted": self.relations_extracted,
                "new": self.relations_new,
                "duplicate": self.relations_duplicate,
                "by_type": self.relations_by_type,
            },
            "confidence": self.confidence_distribution,
        }


class EnrichmentAnalytics:
    """
    Analytics for knowledge graph enrichment.
    """
    
    def __init__(self):
        """Initialize analytics."""
        self.baseline_stats: Optional[BaselineStats] = None
        self.enrichment_stats: Optional[EnrichmentStats] = None
        
        # Try to connect to Neo4j for live stats
        self.neo4j_connected = False
        self.driver = None
    
    def _try_neo4j_connection(self) -> bool:
        """Try to connect to Neo4j for live statistics."""
        try:
            from neo4j import GraphDatabase
            
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
            )
            
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self.neo4j_connected = True
            logger.info("Connected to Neo4j for analytics")
            return True
            
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")
            return False
    
    def load_baseline_stats(self) -> BaselineStats:
        """
        Load baseline statistics from CSV files.
        
        Returns:
            BaselineStats object
        """
        stats = BaselineStats()
        
        # Count entities from CSV files
        entity_files = {
            "players": PROCESSED_DATA_DIR / "players_clean.csv",
            "coaches": PROCESSED_DATA_DIR / "coaches_clean.csv",
            "clubs": PROCESSED_DATA_DIR / "clubs_clean.csv",
            "national_teams": PROCESSED_DATA_DIR / "national_teams_clean.csv",
            "stadiums": PROCESSED_DATA_DIR / "stadiums_clean.csv",
            "competitions": PROCESSED_DATA_DIR / "competitions_clean.csv",
        }
        
        for entity_type, file_path in entity_files.items():
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    count = len(df)
                    
                    if entity_type == "players":
                        stats.total_players = count
                    elif entity_type == "coaches":
                        stats.total_coaches = count
                    elif entity_type == "clubs":
                        stats.total_clubs = count
                    elif entity_type == "national_teams":
                        stats.total_national_teams = count
                    elif entity_type == "stadiums":
                        stats.total_stadiums = count
                    elif entity_type == "competitions":
                        stats.total_competitions = count
                        
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")
        
        # Count edges from edge files
        edges_dir = DATA_DIR / "edges"
        if edges_dir.exists():
            for edge_file in edges_dir.glob("*.csv"):
                try:
                    df = pd.read_csv(edge_file)
                    edge_type = edge_file.stem.upper()
                    count = len(df)
                    stats.edge_types[edge_type] = count
                    stats.total_edges += count
                except Exception as e:
                    logger.warning(f"Error reading {edge_file}: {e}")
        
        self.baseline_stats = stats
        return stats
    
    def load_enrichment_stats(self) -> EnrichmentStats:
        """
        Load enrichment statistics from output files.
        
        Returns:
            EnrichmentStats object
        """
        stats = EnrichmentStats()
        
        # Load recognized entities stats
        entities_file = ENRICHMENT_DIR / "recognized_entities.jsonl"
        if entities_file.exists():
            with open(entities_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        entities = record.get("entities", [])
                        
                        for entity in entities:
                            stats.entities_recognized += 1
                            
                            entity_type = entity.get("type", "UNKNOWN")
                            if entity_type not in stats.entities_by_type:
                                stats.entities_by_type[entity_type] = 0
                            stats.entities_by_type[entity_type] += 1
                            
                            # Check if linked
                            if entity.get("wiki_id"):
                                stats.entities_linked += 1
                            else:
                                stats.entities_new += 1
                            
                            # Confidence distribution
                            confidence = entity.get("confidence", 0.0)
                            if confidence >= 0.85:
                                level = "high"
                            elif confidence >= 0.70:
                                level = "medium"
                            else:
                                level = "low"
                            
                            if level not in stats.confidence_distribution:
                                stats.confidence_distribution[level] = 0
                            stats.confidence_distribution[level] += 1
                            
                    except json.JSONDecodeError:
                        continue
        
        # Load extracted relations stats
        relations_file = ENRICHMENT_DIR / "extracted_relations.jsonl"
        if relations_file.exists():
            with open(relations_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        relations = record.get("relations", [])
                        
                        for relation in relations:
                            stats.relations_extracted += 1
                            
                            rel_type = relation.get("predicate", "UNKNOWN")
                            if rel_type not in stats.relations_by_type:
                                stats.relations_by_type[rel_type] = 0
                            stats.relations_by_type[rel_type] += 1
                            
                    except json.JSONDecodeError:
                        continue
        
        # Load validation stats for new vs duplicate
        validated_file = ENRICHMENT_DIR / "validated_relations.jsonl"
        if validated_file.exists():
            with open(validated_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        relations = record.get("relations", [])
                        
                        for relation in relations:
                            validation = relation.get("validation", {})
                            status = validation.get("status", "unknown")
                            
                            if status == "duplicate":
                                stats.relations_duplicate += 1
                            elif status in ["valid", "new"]:
                                stats.relations_new += 1
                            
                    except json.JSONDecodeError:
                        continue
        
        self.enrichment_stats = stats
        return stats
    
    def get_neo4j_stats(self) -> Optional[Dict]:
        """
        Get live statistics from Neo4j.
        
        Returns:
            Dict with Neo4j statistics or None
        """
        if not self.neo4j_connected:
            if not self._try_neo4j_connection():
                return None
        
        try:
            with self.driver.session() as session:
                # Count nodes by label
                node_counts = {}
                labels = ["Player", "Coach", "Club", "NationalTeam", "Stadium", "Competition"]
                
                for label in labels:
                    result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    record = result.single()
                    node_counts[label] = record["count"] if record else 0
                
                # Count relationships by type
                rel_result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(r) as count
                """)
                rel_counts = {record["type"]: record["count"] for record in rel_result}
                
                # Count enriched items (with source tag)
                enriched_result = session.run("""
                    MATCH (n)
                    WHERE n.source = 'text_extraction' OR n.enrichment_source = 'text_extraction'
                    RETURN labels(n)[0] as label, count(n) as count
                """)
                enriched_counts = {record["label"]: record["count"] for record in enriched_result}
                
                return {
                    "node_counts": node_counts,
                    "relationship_counts": rel_counts,
                    "enriched_counts": enriched_counts,
                }
                
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return None
    
    def compute_growth(self) -> Dict:
        """
        Compute growth from baseline to current state.
        
        Returns:
            Growth statistics dict
        """
        if not self.baseline_stats:
            self.load_baseline_stats()
        
        if not self.enrichment_stats:
            self.load_enrichment_stats()
        
        baseline = self.baseline_stats
        enriched = self.enrichment_stats
        
        growth = {
            "baseline": baseline.to_dict(),
            "enrichment": enriched.to_dict(),
            "growth": {
                "new_entity_candidates": enriched.entities_new,
                "entities_linked": enriched.entities_linked,
                "new_relations": enriched.relations_new,
                "relation_types_discovered": list(enriched.relations_by_type.keys()),
            },
            "projected": {
                "players": baseline.total_players + (enriched.entities_by_type.get("PLAYER", 0) - enriched.entities_linked),
                "coaches": baseline.total_coaches + enriched.entities_by_type.get("COACH", 0),
                "clubs": baseline.total_clubs + enriched.entities_by_type.get("CLUB", 0),
                "total_edges": baseline.total_edges + enriched.relations_new,
            },
        }
        
        return growth
    
    def compute_quality_metrics(self) -> Dict:
        """
        Compute quality metrics for the enrichment.
        
        Returns:
            Quality metrics dict
        """
        if not self.enrichment_stats:
            self.load_enrichment_stats()
        
        stats = self.enrichment_stats
        
        # Entity linking rate
        if stats.entities_recognized > 0:
            linking_rate = stats.entities_linked / stats.entities_recognized
        else:
            linking_rate = 0.0
        
        # Confidence distribution
        total_conf = sum(stats.confidence_distribution.values())
        conf_percentages = {}
        if total_conf > 0:
            for level, count in stats.confidence_distribution.items():
                conf_percentages[level] = count / total_conf
        
        # Relation extraction rate (estimated)
        # Assume ~50 relations per 100 sentences as target
        target_relations_per_100_sentences = 50
        # We'd need sentence count to compute this properly
        
        return {
            "entity_metrics": {
                "total_recognized": stats.entities_recognized,
                "linking_rate": linking_rate,
                "new_candidates": stats.entities_new,
            },
            "relation_metrics": {
                "total_extracted": stats.relations_extracted,
                "new_relations": stats.relations_new,
                "duplicate_rate": stats.relations_duplicate / max(stats.relations_extracted, 1),
            },
            "confidence_distribution": conf_percentages,
            "top_relation_types": dict(
                sorted(stats.relations_by_type.items(), key=lambda x: -x[1])[:10]
            ),
            "top_entity_types": dict(
                sorted(stats.entities_by_type.items(), key=lambda x: -x[1])[:10]
            ),
        }
    
    def generate_report(
        self,
        output_file: Optional[Path] = None,
    ) -> Dict:
        """
        Generate comprehensive analytics report.
        
        Args:
            output_file: Optional output file path
            
        Returns:
            Full report dict
        """
        report = {
            "baseline_stats": self.load_baseline_stats().to_dict(),
            "enrichment_stats": self.load_enrichment_stats().to_dict(),
            "growth": self.compute_growth(),
            "quality_metrics": self.compute_quality_metrics(),
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        # Add Neo4j live stats if available
        neo4j_stats = self.get_neo4j_stats()
        if neo4j_stats:
            report["neo4j_current"] = neo4j_stats
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"Report saved to {output_file}")
        
        return report
    
    def print_summary(self) -> None:
        """Print a summary of analytics to console."""
        baseline = self.load_baseline_stats()
        enriched = self.load_enrichment_stats()
        quality = self.compute_quality_metrics()
        
        print("\n" + "="*60)
        print("VIETNAM FOOTBALL KNOWLEDGE GRAPH - ENRICHMENT ANALYTICS")
        print("="*60)
        
        print("\n📊 BASELINE (Pre-Enrichment)")
        print("-"*40)
        print(f"  Players:        {baseline.total_players:,}")
        print(f"  Coaches:        {baseline.total_coaches:,}")
        print(f"  Clubs:          {baseline.total_clubs:,}")
        print(f"  National Teams: {baseline.total_national_teams:,}")
        print(f"  Stadiums:       {baseline.total_stadiums:,}")
        print(f"  Competitions:   {baseline.total_competitions:,}")
        print(f"  Total Edges:    {baseline.total_edges:,}")
        
        print("\n🔍 ENRICHMENT RESULTS")
        print("-"*40)
        print(f"  Entities Recognized: {enriched.entities_recognized:,}")
        print(f"  - Linked to Existing: {enriched.entities_linked:,}")
        print(f"  - New Candidates:     {enriched.entities_new:,}")
        print(f"  Relations Extracted:  {enriched.relations_extracted:,}")
        print(f"  - New Relations:      {enriched.relations_new:,}")
        print(f"  - Duplicates:         {enriched.relations_duplicate:,}")
        
        print("\n📈 QUALITY METRICS")
        print("-"*40)
        print(f"  Entity Linking Rate: {quality['entity_metrics']['linking_rate']:.1%}")
        if quality['confidence_distribution']:
            print(f"  High Confidence:     {quality['confidence_distribution'].get('high', 0):.1%}")
            print(f"  Medium Confidence:   {quality['confidence_distribution'].get('medium', 0):.1%}")
            print(f"  Low Confidence:      {quality['confidence_distribution'].get('low', 0):.1%}")
        
        print("\n📋 TOP RELATION TYPES")
        print("-"*40)
        for rel_type, count in list(quality['top_relation_types'].items())[:5]:
            print(f"  {rel_type}: {count:,}")
        
        print("\n📋 TOP ENTITY TYPES")
        print("-"*40)
        for entity_type, count in list(quality['top_entity_types'].items())[:5]:
            print(f"  {entity_type}: {count:,}")
        
        print("\n" + "="*60)


def main():
    """CLI entry point for enrichment analytics."""
    parser = argparse.ArgumentParser(
        description="Analytics for Vietnam Football KG Enrichment"
    )
    
    parser.add_argument(
        "--show-growth",
        action="store_true",
        help="Show growth statistics",
    )
    parser.add_argument(
        "--compare-with-baseline",
        action="store_true",
        help="Compare current state with baseline",
    )
    parser.add_argument(
        "--quality-metrics",
        action="store_true",
        help="Show quality metrics",
    )
    parser.add_argument(
        "--full-report",
        action="store_true",
        help="Generate full analytics report",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for report (JSON)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary to console",
    )
    
    args = parser.parse_args()
    
    analytics = EnrichmentAnalytics()
    
    if args.summary or not any([args.show_growth, args.compare_with_baseline, 
                                args.quality_metrics, args.full_report]):
        analytics.print_summary()
        return
    
    if args.show_growth:
        print("\n=== Growth Statistics ===")
        growth = analytics.compute_growth()
        print(json.dumps(growth, indent=2, ensure_ascii=False))
        return
    
    if args.compare_with_baseline:
        print("\n=== Baseline Comparison ===")
        baseline = analytics.load_baseline_stats()
        enriched = analytics.load_enrichment_stats()
        
        print("\nBaseline:")
        print(json.dumps(baseline.to_dict(), indent=2))
        print("\nEnrichment:")
        print(json.dumps(enriched.to_dict(), indent=2))
        return
    
    if args.quality_metrics:
        print("\n=== Quality Metrics ===")
        metrics = analytics.compute_quality_metrics()
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
        return
    
    if args.full_report:
        output_file = Path(args.output) if args.output else REPORTS_DIR / "enrichment_analytics.json"
        print(f"\n=== Generating Full Report ===")
        report = analytics.generate_report(output_file)
        print(f"Report saved to {output_file}")
        return


if __name__ == "__main__":
    main()
