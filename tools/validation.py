"""
Validation Tool for Vietnam Football Knowledge Graph

This module validates the imported data in Neo4j and generates a report.

Features:
- Counts nodes by type (Player, Coach, Club, etc.)
- Counts relationships by type
- Checks for orphan nodes
- Runs sample queries for verification
- Generates a comprehensive report

Usage:
    python -m tools.validation --neo4j-uri neo4j+s://xxx.databases.neo4j.io --user neo4j --password yourpassword
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    REPORTS_DIR,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class GraphValidator:
    """
    Validator for the Vietnam Football Knowledge Graph.
    """
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
    ):
        """
        Initialize the validator.
        
        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.report_lines: List[str] = []
    
    def connect(self) -> bool:
        """Connect to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {self.uri}")
            return True
        except (AuthError, ServiceUnavailable) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the connection."""
        if self.driver:
            self.driver.close()
    
    def run_query(
        self,
        query: str,
        parameters: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Run a query and return results as list of dicts."""
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def _add_report_line(self, line: str = ""):
        """Add a line to the report."""
        self.report_lines.append(line)
        print(line)
    
    def _add_report_section(self, title: str):
        """Add a section header to the report."""
        self._add_report_line("")
        self._add_report_line("=" * 60)
        self._add_report_line(title)
        self._add_report_line("=" * 60)
    
    def count_nodes(self) -> Dict[str, int]:
        """Count nodes by label."""
        self._add_report_section("NODE COUNTS")
        
        labels = ["Player", "Coach", "Club", "NationalTeam", "Position", "Nationality"]
        counts = {}
        
        for label in labels:
            query = f"MATCH (n:{label}) RETURN count(n) AS count"
            result = self.run_query(query)
            count = result[0]["count"] if result else 0
            counts[label] = count
            self._add_report_line(f"  {label}: {count}")
        
        # Total
        total = sum(counts.values())
        self._add_report_line("-" * 40)
        self._add_report_line(f"  TOTAL NODES: {total}")
        
        return counts
    
    def count_relationships(self) -> Dict[str, int]:
        """Count relationships by type."""
        self._add_report_section("RELATIONSHIP COUNTS")
        
        rel_types = [
            "PLAYED_FOR",
            "PLAYED_FOR_NATIONAL",
            "COACHED",
            "COACHED_NATIONAL",
            "TEAMMATE",
            "NATIONAL_TEAMMATE",
            "UNDER_COACH",
            "HAS_POSITION",
            "HAS_NATIONALITY",
        ]
        counts = {}
        
        for rel_type in rel_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count"
            result = self.run_query(query)
            count = result[0]["count"] if result else 0
            counts[rel_type] = count
            self._add_report_line(f"  {rel_type}: {count}")
        
        # For undirected relationships, count differently
        for rel_type in ["TEAMMATE", "NATIONAL_TEAMMATE"]:
            query = f"MATCH ()-[r:{rel_type}]-() RETURN count(r)/2 AS count"
            result = self.run_query(query)
            if result:
                counts[rel_type] = int(result[0]["count"])
        
        total = sum(counts.values())
        self._add_report_line("-" * 40)
        self._add_report_line(f"  TOTAL RELATIONSHIPS: {total}")
        
        return counts
    
    def check_orphan_nodes(self) -> Dict[str, int]:
        """Check for orphan nodes (nodes with no relationships)."""
        self._add_report_section("ORPHAN NODE CHECK")
        
        orphans = {}
        
        # Players without PLAYED_FOR
        query = """
        MATCH (p:Player)
        WHERE NOT (p)-[:PLAYED_FOR]->()
        RETURN count(p) AS count
        """
        result = self.run_query(query)
        count = result[0]["count"] if result else 0
        orphans["players_without_clubs"] = count
        self._add_report_line(f"  Players without PLAYED_FOR: {count}")
        
        # Coaches without COACHED
        query = """
        MATCH (c:Coach)
        WHERE NOT (c)-[:COACHED]->() AND NOT (c)-[:COACHED_NATIONAL]->()
        RETURN count(c) AS count
        """
        result = self.run_query(query)
        count = result[0]["count"] if result else 0
        orphans["coaches_without_clubs"] = count
        self._add_report_line(f"  Coaches without clubs: {count}")
        
        # Clubs without any players
        query = """
        MATCH (cl:Club)
        WHERE NOT ()-[:PLAYED_FOR]->(cl)
        RETURN count(cl) AS count
        """
        result = self.run_query(query)
        count = result[0]["count"] if result else 0
        orphans["clubs_without_players"] = count
        self._add_report_line(f"  Clubs without players: {count}")
        
        # Completely disconnected nodes
        query = """
        MATCH (n)
        WHERE NOT (n)--()
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
        """
        result = self.run_query(query)
        if result:
            self._add_report_line("\n  Completely disconnected nodes:")
            for row in result:
                label = row["label"]
                count = row["count"]
                orphans[f"disconnected_{label}"] = count
                self._add_report_line(f"    {label}: {count}")
        
        return orphans
    
    def sample_queries(self) -> Dict[str, List[Dict]]:
        """Run sample queries to verify data quality."""
        self._add_report_section("SAMPLE QUERIES")
        
        results = {}
        
        # Top 10 players by number of clubs played for
        self._add_report_line("\n  Top 10 players by clubs played for:")
        query = """
        MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club)
        RETURN p.name AS player, count(DISTINCT c) AS clubs
        ORDER BY clubs DESC
        LIMIT 10
        """
        result = self.run_query(query)
        results["top_players_by_clubs"] = result
        for row in result:
            self._add_report_line(f"    {row['player']}: {row['clubs']} clubs")
        
        # Top 10 players by teammate count
        self._add_report_line("\n  Top 10 players by teammate count:")
        query = """
        MATCH (p:Player)-[:TEAMMATE]-(teammate:Player)
        RETURN p.name AS player, count(DISTINCT teammate) AS teammates
        ORDER BY teammates DESC
        LIMIT 10
        """
        result = self.run_query(query)
        results["top_players_by_teammates"] = result
        for row in result:
            self._add_report_line(f"    {row['player']}: {row['teammates']} teammates")
        
        # Top coaches by clubs managed
        self._add_report_line("\n  Top coaches by clubs managed:")
        query = """
        MATCH (c:Coach)-[:COACHED]->(club:Club)
        RETURN c.name AS coach, count(DISTINCT club) AS clubs
        ORDER BY clubs DESC
        LIMIT 10
        """
        result = self.run_query(query)
        results["top_coaches_by_clubs"] = result
        for row in result:
            self._add_report_line(f"    {row['coach']}: {row['clubs']} clubs")
        
        # Position distribution
        self._add_report_line("\n  Players by position:")
        query = """
        MATCH (p:Player)-[:HAS_POSITION]->(pos:Position)
        RETURN pos.position_code AS position, count(p) AS players
        ORDER BY players DESC
        """
        result = self.run_query(query)
        results["position_distribution"] = result
        for row in result:
            self._add_report_line(f"    {row['position']}: {row['players']} players")
        
        # Clubs with most players
        self._add_report_line("\n  Top 10 clubs by player count:")
        query = """
        MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
        RETURN c.name AS club, count(DISTINCT p) AS players
        ORDER BY players DESC
        LIMIT 10
        """
        result = self.run_query(query)
        results["top_clubs_by_players"] = result
        for row in result:
            self._add_report_line(f"    {row['club']}: {row['players']} players")
        
        return results
    
    def check_data_quality(self) -> Dict[str, Any]:
        """Check data quality issues."""
        self._add_report_section("DATA QUALITY CHECK")
        
        issues = {}
        
        # Players with missing names
        query = """
        MATCH (p:Player)
        WHERE p.name IS NULL OR p.name = ''
        RETURN count(p) AS count
        """
        result = self.run_query(query)
        count = result[0]["count"] if result else 0
        issues["players_missing_name"] = count
        self._add_report_line(f"  Players with missing name: {count}")
        
        # Players with missing position
        query = """
        MATCH (p:Player)
        WHERE p.position IS NULL OR p.position = ''
        RETURN count(p) AS count
        """
        result = self.run_query(query)
        count = result[0]["count"] if result else 0
        issues["players_missing_position"] = count
        self._add_report_line(f"  Players with missing position: {count}")
        
        # Players with missing nationality
        query = """
        MATCH (p:Player)
        WHERE p.nationality IS NULL OR p.nationality = ''
        RETURN count(p) AS count
        """
        result = self.run_query(query)
        count = result[0]["count"] if result else 0
        issues["players_missing_nationality"] = count
        self._add_report_line(f"  Players with missing nationality: {count}")
        
        # Relationships with missing years
        query = """
        MATCH ()-[r:PLAYED_FOR]->()
        WHERE r.from_year IS NULL
        RETURN count(r) AS count
        """
        result = self.run_query(query)
        count = result[0]["count"] if result else 0
        issues["played_for_missing_year"] = count
        self._add_report_line(f"  PLAYED_FOR without from_year: {count}")
        
        return issues
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation checks."""
        if not self.connect():
            return {"error": "Failed to connect to Neo4j"}
        
        try:
            self.report_lines = []
            
            # Header
            self._add_report_line("=" * 60)
            self._add_report_line("VIETNAM FOOTBALL KNOWLEDGE GRAPH - VALIDATION REPORT")
            self._add_report_line(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._add_report_line("=" * 60)
            
            results = {
                "node_counts": self.count_nodes(),
                "relationship_counts": self.count_relationships(),
                "orphan_nodes": self.check_orphan_nodes(),
                "sample_queries": self.sample_queries(),
                "data_quality": self.check_data_quality(),
            }
            
            # Summary
            self._add_report_section("SUMMARY")
            total_nodes = sum(results["node_counts"].values())
            total_rels = sum(results["relationship_counts"].values())
            self._add_report_line(f"  Total nodes: {total_nodes}")
            self._add_report_line(f"  Total relationships: {total_rels}")
            
            # Quality score (simple heuristic)
            orphan_count = sum(
                v for k, v in results["orphan_nodes"].items()
                if k.startswith("disconnected_")
            )
            quality_issues = sum(results["data_quality"].values())
            
            if total_nodes > 0:
                quality_score = max(0, 100 - (orphan_count + quality_issues) / total_nodes * 100)
            else:
                quality_score = 0
            
            self._add_report_line(f"  Data quality score: {quality_score:.1f}%")
            
            return results
            
        finally:
            self.close()
    
    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """
        Save the report to a file.
        
        Args:
            output_path: Path to save the report (default: reports/import_report.txt)
            
        Returns:
            Path to the saved report
        """
        if output_path is None:
            output_path = REPORTS_DIR / "import_report.txt"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.report_lines))
        
        logger.info(f"Report saved to {output_path}")
        return output_path


def main():
    """Main entry point for the validation CLI."""
    parser = argparse.ArgumentParser(
        description="Validate the Vietnam Football Knowledge Graph in Neo4j",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run validation:
    python -m tools.validation --neo4j-uri neo4j+s://xxx.databases.neo4j.io --user neo4j --password yourpassword
    
  Save report to custom location:
    python -m tools.validation --output reports/my_report.txt
        """,
    )
    
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        default=NEO4J_URI,
        help="Neo4j connection URI",
    )
    parser.add_argument(
        "--user",
        type=str,
        default=NEO4J_USER,
        help="Neo4j username",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=NEO4J_PASSWORD,
        help="Neo4j password",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for the report",
    )
    
    args = parser.parse_args()
    
    # Validate connection params
    if not args.neo4j_uri or "xxx" in args.neo4j_uri:
        print("Error: Please provide a valid Neo4j URI")
        sys.exit(1)
    
    # Create validator and run
    validator = GraphValidator(
        uri=args.neo4j_uri,
        user=args.user,
        password=args.password,
    )
    
    results = validator.run_all_validations()
    
    if "error" not in results:
        output_path = Path(args.output) if args.output else None
        validator.save_report(output_path)


if __name__ == "__main__":
    main()
