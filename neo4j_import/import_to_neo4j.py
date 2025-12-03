"""
Neo4j Import Script for Vietnam Football Knowledge Graph

This module imports the processed CSV data into Neo4j Aura.

Since Neo4j Aura doesn't support file:/// URLs, this script:
1. Reads CSV files from local disk
2. Converts them to Cypher statements
3. Executes statements directly via the Neo4j Python driver

Usage:
    python -m neo4j_import.import_to_neo4j --uri neo4j+s://xxx.databases.neo4j.io --user neo4j --password yourpassword
    python -m neo4j_import.import_to_neo4j --reset  # Drop all data first
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import (
    EDGES_DATA_DIR,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    PROCESSED_DATA_DIR,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Neo4jImporter:
    """
    Importer for loading data into Neo4j Aura.
    
    Uses the Neo4j Python driver to execute Cypher statements directly,
    which works with Neo4j Aura (unlike LOAD CSV with file:// URLs).
    """
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        batch_size: int = 500,
    ):
        """
        Initialize the importer.
        
        Args:
            uri: Neo4j connection URI (e.g., neo4j+s://xxx.databases.neo4j.io)
            user: Neo4j username
            password: Neo4j password
            batch_size: Number of records to process per transaction
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.batch_size = batch_size
        self.driver = None
        self.stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": 0,
        }
    
    def connect(self) -> bool:
        """
        Connect to Neo4j.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Verify connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            logger.info(f"Connected to Neo4j at {self.uri}")
            return True
        except AuthError as e:
            logger.error(f"Authentication failed: {e}")
            return False
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    def run_query(
        self,
        query: str,
        parameters: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Run a single Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query result summary or None on error
        """
        try:
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
        except Exception as e:
            logger.error(f"Query failed: {e}")
            self.stats["errors"] += 1
            return None
    
    def run_batch(
        self,
        query: str,
        batch: List[Dict],
        description: str = "Processing",
    ) -> int:
        """
        Run a parameterized query for a batch of records.
        
        Args:
            query: Cypher query with $batch parameter
            batch: List of record dictionaries
            description: Description for logging
            
        Returns:
            Number of records processed
        """
        if not batch:
            return 0
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {"batch": batch})
                summary = result.consume()
                
                nodes = summary.counters.nodes_created
                rels = summary.counters.relationships_created
                
                self.stats["nodes_created"] += nodes
                self.stats["relationships_created"] += rels
                
                return len(batch)
        except Exception as e:
            logger.error(f"Batch query failed: {e}")
            self.stats["errors"] += 1
            return 0
    
    def reset_database(self):
        """Drop all nodes and relationships."""
        logger.warning("Resetting database - deleting all data...")
        
        # Delete in batches to avoid memory issues
        query = """
        MATCH (n)
        WITH n LIMIT 10000
        DETACH DELETE n
        RETURN count(*) as deleted
        """
        
        total_deleted = 0
        while True:
            result = self.run_query(query)
            if result and result.get("nodes_deleted", 0) > 0:
                total_deleted += result["nodes_deleted"]
                logger.info(f"Deleted {total_deleted} nodes so far...")
            else:
                break
        
        logger.info(f"Database reset complete. Deleted {total_deleted} nodes.")
    
    def create_schema(self):
        """Create constraints and indexes."""
        logger.info("Creating schema (constraints and indexes)...")
        
        schema_queries = [
            # Constraints
            "CREATE CONSTRAINT player_wiki_id_unique IF NOT EXISTS FOR (p:Player) REQUIRE p.wiki_id IS UNIQUE",
            "CREATE CONSTRAINT coach_wiki_id_unique IF NOT EXISTS FOR (c:Coach) REQUIRE c.wiki_id IS UNIQUE",
            "CREATE CONSTRAINT club_wiki_id_unique IF NOT EXISTS FOR (cl:Club) REQUIRE cl.wiki_id IS UNIQUE",
            "CREATE CONSTRAINT national_team_wiki_id_unique IF NOT EXISTS FOR (nt:NationalTeam) REQUIRE nt.wiki_id IS UNIQUE",
            # Position is now a property on Player, not a separate node
            "CREATE CONSTRAINT province_id_unique IF NOT EXISTS FOR (prov:Province) REQUIRE prov.province_id IS UNIQUE",
            "CREATE CONSTRAINT stadium_wiki_id_unique IF NOT EXISTS FOR (st:Stadium) REQUIRE st.wiki_id IS UNIQUE",
            "CREATE CONSTRAINT competition_wiki_id_unique IF NOT EXISTS FOR (comp:Competition) REQUIRE comp.wiki_id IS UNIQUE",
            
            # Indexes
            "CREATE INDEX player_name_index IF NOT EXISTS FOR (p:Player) ON (p.name)",
            "CREATE INDEX player_position_index IF NOT EXISTS FOR (p:Player) ON (p.position)",
            "CREATE INDEX coach_name_index IF NOT EXISTS FOR (c:Coach) ON (c.name)",
            "CREATE INDEX club_name_index IF NOT EXISTS FOR (cl:Club) ON (cl.name)",
            "CREATE INDEX national_team_name_index IF NOT EXISTS FOR (nt:NationalTeam) ON (nt.name)",
            "CREATE INDEX province_name_index IF NOT EXISTS FOR (prov:Province) ON (prov.name)",
            "CREATE INDEX player_birth_year_index IF NOT EXISTS FOR (p:Player) ON (p.birth_year)",
            "CREATE INDEX stadium_name_index IF NOT EXISTS FOR (st:Stadium) ON (st.name)",
            "CREATE INDEX competition_name_index IF NOT EXISTS FOR (comp:Competition) ON (comp.name)",
            "CREATE INDEX competition_year_index IF NOT EXISTS FOR (comp:Competition) ON (comp.season_year)",
        ]
        
        for query in schema_queries:
            result = self.run_query(query)
            if result is not None:
                logger.debug(f"Schema query executed: {query[:50]}...")
        
        logger.info("Schema creation complete")
    
    def load_csv(self, filename: str, directory: Path = PROCESSED_DATA_DIR) -> List[Dict]:
        """
        Load a CSV file into a list of dictionaries.
        
        Args:
            filename: Name of the CSV file
            directory: Directory containing the file
            
        Returns:
            List of row dictionaries
        """
        file_path = directory / filename
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []
        
        rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert empty strings to None
                cleaned_row = {
                    k: (v if v != "" else None)
                    for k, v in row.items()
                }
                rows.append(cleaned_row)
        
        logger.info(f"Loaded {len(rows)} rows from {filename}")
        return rows
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert a value to integer."""
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def import_positions(self):
        """Import position reference data."""
        rows = self.load_csv("positions_reference.csv")
        if not rows:
            return
        
        query = """
        UNWIND $batch AS row
        MERGE (pos:Position {position_id: row.position_id})
        SET pos.position_code = row.position_code,
            pos.position_name = row.position_name
        """
        
        count = self.run_batch(query, rows, "Importing positions")
        logger.info(f"Imported {count} positions")
    
    def import_nationalities(self):
        """Import nationality reference data."""
        rows = self.load_csv("nationalities_reference.csv")
        if not rows:
            return
        
        # Convert nationality_id to integer
        for row in rows:
            row["nationality_id"] = self._safe_int(row.get("nationality_id"))
        
        query = """
        UNWIND $batch AS row
        MERGE (nat:Nationality {nationality_id: row.nationality_id})
        SET nat.nationality_name = row.nationality_name,
            nat.country_code = row.country_code
        """
        
        count = self.run_batch(query, rows, "Importing nationalities")
        logger.info(f"Imported {count} nationalities")
    
    def import_players(self):
        """Import player nodes (Vietnamese players only)."""
        # Try to load Vietnamese players first, fallback to all players
        rows = self.load_csv("players_vn_clean.csv")
        if not rows:
            logger.warning("No Vietnamese players file found, trying players_clean.csv")
            rows = self.load_csv("players_clean.csv")
        if not rows:
            return
        
        # Convert numeric fields
        for row in rows:
            row["wiki_id"] = self._safe_int(row.get("wiki_id"))
            row["birth_year"] = self._safe_int(row.get("birth_year"))
            row["club_appearances"] = self._safe_int(row.get("club_appearances"))
            row["club_goals"] = self._safe_int(row.get("club_goals"))
            row["national_team_appearances"] = self._safe_int(row.get("national_team_appearances"))
            row["national_team_goals"] = self._safe_int(row.get("national_team_goals"))
            row["career_start_year"] = self._safe_int(row.get("career_start_year"))
            row["career_end_year"] = self._safe_int(row.get("career_end_year"))
            row["years_active"] = self._safe_int(row.get("years_active"))
            # Handle height_m as float
            height_m = row.get("height_m")
            row["height_m"] = float(height_m) if height_m and height_m != "" else None
            # Handle boolean
            is_national = row.get("is_national_team_player", "")
            row["is_national_team_player"] = str(is_national).lower() == "true" if is_national else False
        
        query = """
        UNWIND $batch AS row
        MERGE (p:Player {wiki_id: row.wiki_id})
        SET p.name = row.name,
            p.canonical_name = row.canonical_name,
            p.full_name = row.full_name,
            p.date_of_birth = row.date_of_birth,
            p.birth_year = row.birth_year,
            p.place_of_birth = row.place_of_birth,
            p.province = row.province,
            p.nationality = row.nationality_normalized,
            p.position = row.position_normalized,
            p.height = row.height,
            p.height_m = row.height_m,
            p.current_club = row.current_club,
            p.wiki_url = row.wiki_url,
            p.club_appearances = row.club_appearances,
            p.club_goals = row.club_goals,
            p.national_team_appearances = row.national_team_appearances,
            p.national_team_goals = row.national_team_goals,
            p.is_national_team_player = row.is_national_team_player,
            p.career_start_year = row.career_start_year,
            p.career_end_year = row.career_end_year,
            p.years_active = row.years_active
        """
        
        # Process in batches
        for i in tqdm(range(0, len(rows), self.batch_size), desc="Importing players"):
            batch = rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(rows)} players")
    
    def import_coaches(self):
        """Import coach nodes."""
        rows = self.load_csv("coaches_clean.csv")
        if not rows:
            return
        
        for row in rows:
            row["wiki_id"] = self._safe_int(row.get("wiki_id"))
        
        query = """
        UNWIND $batch AS row
        MERGE (c:Coach {wiki_id: row.wiki_id})
        SET c.name = row.name,
            c.canonical_name = row.canonical_name,
            c.full_name = row.full_name,
            c.date_of_birth = row.date_of_birth,
            c.nationality = row.nationality_normalized,
            c.wiki_url = row.wiki_url
        """
        
        for i in tqdm(range(0, len(rows), self.batch_size), desc="Importing coaches"):
            batch = rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(rows)} coaches")
    
    def import_clubs(self):
        """Import club nodes."""
        rows = self.load_csv("clubs_clean.csv")
        if not rows:
            return
        
        for row in rows:
            row["wiki_id"] = self._safe_int(row.get("wiki_id"))
            row["founded"] = self._safe_int(row.get("founded"))
        
        query = """
        UNWIND $batch AS row
        MERGE (cl:Club {wiki_id: row.wiki_id})
        SET cl.name = row.name,
            cl.canonical_name = row.canonical_name,
            cl.short_name = row.short_name,
            cl.full_name = row.full_name,
            cl.founded = row.founded,
            cl.ground = row.ground,
            cl.capacity = row.capacity,
            cl.chairman = row.chairman,
            cl.manager = row.manager,
            cl.league = row.league,
            cl.country = row.country,
            cl.wiki_url = row.wiki_url
        """
        
        for i in tqdm(range(0, len(rows), self.batch_size), desc="Importing clubs"):
            batch = rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(rows)} clubs")
    
    def import_national_teams(self):
        """Import national team nodes."""
        rows = self.load_csv("national_teams_clean.csv")
        if not rows:
            return
        
        for row in rows:
            row["wiki_id"] = self._safe_int(row.get("wiki_id"))
        
        query = """
        UNWIND $batch AS row
        MERGE (nt:NationalTeam {wiki_id: row.wiki_id})
        SET nt.name = row.name,
            nt.canonical_name = row.canonical_name,
            nt.team_level = row.team_level,
            nt.gender = row.gender,
            nt.wiki_url = row.wiki_url
        """
        
        for i in tqdm(range(0, len(rows), self.batch_size), desc="Importing national teams"):
            batch = rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(rows)} national teams")
    
    def import_provinces(self):
        """Import province reference data."""
        rows = self.load_csv("provinces_reference.csv")
        if not rows:
            return
        
        for row in rows:
            row["province_id"] = self._safe_int(row.get("province_id"))
        
        query = """
        UNWIND $batch AS row
        MERGE (prov:Province {province_id: row.province_id})
        SET prov.name = row.name,
            prov.type = row.type,
            prov.region = row.region
        """
        
        count = self.run_batch(query, rows, "Importing provinces")
        logger.info(f"Imported {count} provinces")
    
    def import_stadiums(self):
        """Import stadium nodes."""
        rows = self.load_csv("stadiums_clean.csv")
        if not rows:
            return
        
        for row in rows:
            row["wiki_id"] = self._safe_int(row.get("wiki_id"))
            row["capacity"] = self._safe_int(row.get("capacity"))
            row["opened_year"] = self._safe_int(row.get("opened_year"))
        
        query = """
        UNWIND $batch AS row
        MERGE (st:Stadium {wiki_id: row.wiki_id})
        SET st.name = row.name,
            st.canonical_name = row.canonical_name,
            st.location = row.location,
            st.province = row.province,
            st.capacity = row.capacity,
            st.surface_type = row.surface_type,
            st.opened_year = row.opened_year,
            st.wiki_url = row.wiki_url
        """
        
        for i in tqdm(range(0, len(rows), self.batch_size), desc="Importing stadiums"):
            batch = rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(rows)} stadiums")
    
    def import_competitions(self):
        """Import competition nodes."""
        rows = self.load_csv("competitions_clean.csv")
        if not rows:
            return
        
        for row in rows:
            row["wiki_id"] = self._safe_int(row.get("wiki_id"))
            row["season_year"] = self._safe_int(row.get("season_year"))
            row["founded"] = self._safe_int(row.get("founded"))
        
        query = """
        UNWIND $batch AS row
        MERGE (comp:Competition {wiki_id: row.wiki_id})
        SET comp.name = row.name,
            comp.canonical_name = row.canonical_name,
            comp.competition_type = row.competition_type,
            comp.season_year = row.season_year,
            comp.country = row.country,
            comp.founded = row.founded,
            comp.teams = row.teams,
            comp.level = row.level,
            comp.current_champion = row.current_champion,
            comp.most_titles = row.most_titles,
            comp.wiki_url = row.wiki_url
        """
        
        for i in tqdm(range(0, len(rows), self.batch_size), desc="Importing competitions"):
            batch = rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(rows)} competitions")
    
    def import_played_for(self):
        """Import PLAYED_FOR relationships."""
        rows = self.load_csv("played_for.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        # Filter to only rows with valid club IDs
        valid_rows = []
        for row in rows:
            player_id = self._safe_int(row.get("from_player_id"))
            club_id = self._safe_int(row.get("to_club_id"))
            
            if player_id is not None and club_id is not None:
                valid_rows.append({
                    "from_player_id": player_id,
                    "to_club_id": club_id,
                    "from_year": self._safe_int(row.get("from_year")),
                    "to_year": self._safe_int(row.get("to_year")),
                    "appearances": self._safe_int(row.get("appearances")),
                    "goals": self._safe_int(row.get("goals")),
                })
        
        if not valid_rows:
            logger.warning("No valid played_for relationships to import")
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p:Player {wiki_id: row.from_player_id})
        MATCH (cl:Club {wiki_id: row.to_club_id})
        MERGE (p)-[r:PLAYED_FOR]->(cl)
        SET r.from_year = row.from_year,
            r.to_year = row.to_year,
            r.appearances = row.appearances,
            r.goals = row.goals
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing played_for"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} played_for relationships")
    
    def import_played_for_national(self):
        """Import PLAYED_FOR_NATIONAL relationships."""
        rows = self.load_csv("played_for_national.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            player_id = self._safe_int(row.get("from_player_id"))
            team_id = self._safe_int(row.get("to_team_id"))
            
            if player_id is not None and team_id is not None:
                valid_rows.append({
                    "from_player_id": player_id,
                    "to_team_id": team_id,
                    "from_year": self._safe_int(row.get("from_year")),
                    "to_year": self._safe_int(row.get("to_year")),
                    "appearances": self._safe_int(row.get("appearances")),
                    "goals": self._safe_int(row.get("goals")),
                })
        
        if not valid_rows:
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p:Player {wiki_id: row.from_player_id})
        MATCH (nt:NationalTeam {wiki_id: row.to_team_id})
        MERGE (p)-[r:PLAYED_FOR_NATIONAL]->(nt)
        SET r.from_year = row.from_year,
            r.to_year = row.to_year,
            r.appearances = row.appearances,
            r.goals = row.goals
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing played_for_national"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} played_for_national relationships")
    
    def import_coached(self):
        """Import COACHED relationships."""
        rows = self.load_csv("coached.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            coach_id = self._safe_int(row.get("from_coach_id"))
            club_id = self._safe_int(row.get("to_club_id"))
            
            if coach_id is not None and club_id is not None:
                valid_rows.append({
                    "from_coach_id": coach_id,
                    "to_club_id": club_id,
                    "from_year": self._safe_int(row.get("from_year")),
                    "to_year": self._safe_int(row.get("to_year")),
                    "role": row.get("role"),
                })
        
        if not valid_rows:
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (c:Coach {wiki_id: row.from_coach_id})
        MATCH (cl:Club {wiki_id: row.to_club_id})
        MERGE (c)-[r:COACHED]->(cl)
        SET r.from_year = row.from_year,
            r.to_year = row.to_year,
            r.role = row.role
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing coached"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} coached relationships")
    
    def import_teammate(self):
        """Import TEAMMATE relationships."""
        rows = self.load_csv("teammate.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            p1_id = self._safe_int(row.get("player1_id"))
            p2_id = self._safe_int(row.get("player2_id"))
            
            if p1_id is not None and p2_id is not None:
                valid_rows.append({
                    "player1_id": p1_id,
                    "player2_id": p2_id,
                    "club_name": row.get("club_name"),
                    "from_year": self._safe_int(row.get("from_year")),
                    "to_year": self._safe_int(row.get("to_year")),
                })
        
        if not valid_rows:
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p1:Player {wiki_id: row.player1_id})
        MATCH (p2:Player {wiki_id: row.player2_id})
        MERGE (p1)-[r:TEAMMATE]-(p2)
        SET r.club_name = row.club_name,
            r.from_year = row.from_year,
            r.to_year = row.to_year
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing teammate"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} teammate relationships")
    
    def import_national_teammate(self):
        """Import NATIONAL_TEAMMATE relationships."""
        rows = self.load_csv("national_teammate.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            p1_id = self._safe_int(row.get("player1_id"))
            p2_id = self._safe_int(row.get("player2_id"))
            
            if p1_id is not None and p2_id is not None:
                valid_rows.append({
                    "player1_id": p1_id,
                    "player2_id": p2_id,
                    "team_name": row.get("team_name"),
                    "from_year": self._safe_int(row.get("from_year")),
                    "to_year": self._safe_int(row.get("to_year")),
                })
        
        if not valid_rows:
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p1:Player {wiki_id: row.player1_id})
        MATCH (p2:Player {wiki_id: row.player2_id})
        MERGE (p1)-[r:NATIONAL_TEAMMATE]-(p2)
        SET r.team_name = row.team_name,
            r.from_year = row.from_year,
            r.to_year = row.to_year
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing national_teammate"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} national_teammate relationships")
    
    def import_under_coach(self):
        """Import UNDER_COACH relationships."""
        rows = self.load_csv("under_coach.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            player_id = self._safe_int(row.get("player_id"))
            coach_id = self._safe_int(row.get("coach_id"))
            
            if player_id is not None and coach_id is not None:
                valid_rows.append({
                    "player_id": player_id,
                    "coach_id": coach_id,
                    "club_name": row.get("club_name"),
                    "from_year": self._safe_int(row.get("from_year")),
                    "to_year": self._safe_int(row.get("to_year")),
                })
        
        if not valid_rows:
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p:Player {wiki_id: row.player_id})
        MATCH (c:Coach {wiki_id: row.coach_id})
        MERGE (p)-[r:UNDER_COACH]->(c)
        SET r.club_name = row.club_name,
            r.from_year = row.from_year,
            r.to_year = row.to_year
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing under_coach"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} under_coach relationships")
    
    def import_has_position(self):
        """Import HAS_POSITION relationships."""
        rows = self.load_csv("has_position.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            player_id = self._safe_int(row.get("player_id"))
            position_id = row.get("position_id")
            
            if player_id is not None and position_id:
                valid_rows.append({
                    "player_id": player_id,
                    "position_id": position_id,
                })
        
        if not valid_rows:
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p:Player {wiki_id: row.player_id})
        MATCH (pos:Position {position_id: row.position_id})
        MERGE (p)-[:HAS_POSITION]->(pos)
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing has_position"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} has_position relationships")
    
    def import_has_nationality(self):
        """Import HAS_NATIONALITY relationships."""
        rows = self.load_csv("has_nationality.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        # Separate players and coaches
        player_rows = []
        coach_rows = []
        
        for row in rows:
            entity_id = self._safe_int(row.get("entity_id"))
            nationality_name = row.get("nationality_name")
            entity_type = row.get("entity_type")
            
            if entity_id is not None and nationality_name:
                item = {
                    "entity_id": entity_id,
                    "nationality_name": nationality_name,
                }
                if entity_type == "player":
                    player_rows.append(item)
                elif entity_type == "coach":
                    coach_rows.append(item)
        
        # Import for players
        if player_rows:
            query = """
            UNWIND $batch AS row
            MATCH (p:Player {wiki_id: row.entity_id})
            MATCH (nat:Nationality {nationality_name: row.nationality_name})
            MERGE (p)-[:HAS_NATIONALITY]->(nat)
            """
            
            for i in tqdm(range(0, len(player_rows), self.batch_size), desc="Importing player nationalities"):
                batch = player_rows[i:i + self.batch_size]
                self.run_batch(query, batch)
        
        # Import for coaches
        if coach_rows:
            query = """
            UNWIND $batch AS row
            MATCH (c:Coach {wiki_id: row.entity_id})
            MATCH (nat:Nationality {nationality_name: row.nationality_name})
            MERGE (c)-[:HAS_NATIONALITY]->(nat)
            """
            
            for i in tqdm(range(0, len(coach_rows), self.batch_size), desc="Importing coach nationalities"):
                batch = coach_rows[i:i + self.batch_size]
                self.run_batch(query, batch)
        
        logger.info(f"Imported {len(player_rows) + len(coach_rows)} has_nationality relationships")
    
    def import_born_in(self):
        """Import BORN_IN relationships (Player -> Province)."""
        rows = self.load_csv("born_in.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            player_id = self._safe_int(row.get("player_wiki_id"))
            province_name = row.get("province_name")
            
            if player_id is not None and province_name:
                valid_rows.append({
                    "player_wiki_id": player_id,
                    "province_name": province_name,
                })
        
        if not valid_rows:
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p:Player {wiki_id: row.player_wiki_id})
        MATCH (prov:Province {name: row.province_name})
        MERGE (p)-[:BORN_IN]->(prov)
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing born_in"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} born_in relationships")
    
    def import_home_stadium(self):
        """Import HOME_STADIUM relationships (Club -> Stadium)."""
        rows = self.load_csv("home_stadium.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            club_id = self._safe_int(row.get("club_id"))
            stadium_id = self._safe_int(row.get("stadium_id"))
            
            if club_id is not None and stadium_id is not None:
                valid_rows.append({
                    "club_id": club_id,
                    "stadium_id": stadium_id,
                })
        
        if not valid_rows:
            logger.warning("No valid home_stadium relationships to import")
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (cl:Club {wiki_id: row.club_id})
        MATCH (st:Stadium {wiki_id: row.stadium_id})
        MERGE (cl)-[:HOME_STADIUM]->(st)
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing home_stadium"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} home_stadium relationships")
    
    def import_stadium_in_province(self):
        """Import STADIUM_IN_PROVINCE relationships (Stadium -> Province)."""
        rows = self.load_csv("stadium_in_province.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            stadium_id = self._safe_int(row.get("stadium_id"))
            province_id = self._safe_int(row.get("province_id"))
            
            if stadium_id is not None and province_id is not None:
                valid_rows.append({
                    "stadium_id": stadium_id,
                    "province_id": province_id,
                })
        
        if not valid_rows:
            logger.warning("No valid stadium_in_province relationships to import")
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (st:Stadium {wiki_id: row.stadium_id})
        MATCH (prov:Province {province_id: row.province_id})
        MERGE (st)-[:LOCATED_IN]->(prov)
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing stadium_in_province"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} stadium_in_province relationships")
    
    def import_club_based_in(self):
        """Import CLUB_BASED_IN relationships (Club -> Province)."""
        rows = self.load_csv("club_based_in.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            club_id = self._safe_int(row.get("club_id"))
            province_id = self._safe_int(row.get("province_id"))
            
            if club_id is not None and province_id is not None:
                valid_rows.append({
                    "club_id": club_id,
                    "province_id": province_id,
                })
        
        if not valid_rows:
            logger.warning("No valid club_based_in relationships to import")
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (cl:Club {wiki_id: row.club_id})
        MATCH (prov:Province {province_id: row.province_id})
        MERGE (cl)-[:BASED_IN]->(prov)
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing club_based_in"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} club_based_in relationships")
    
    def import_competes_in(self):
        """Import COMPETES_IN relationships (Club -> Competition)."""
        rows = self.load_csv("competes_in.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            club_id = self._safe_int(row.get("club_id"))
            competition_id = self._safe_int(row.get("competition_id"))
            competition_name = row.get("competition_name", "")
            
            if club_id is not None:
                valid_rows.append({
                    "club_id": club_id,
                    "competition_id": competition_id,
                    "competition_name": competition_name,
                })
        
        if not valid_rows:
            logger.warning("No valid competes_in relationships to import")
            return
        
        # Create relationships with matched competitions
        matched = [r for r in valid_rows if r["competition_id"] is not None]
        if matched:
            query = """
            UNWIND $batch AS row
            MATCH (cl:Club {wiki_id: row.club_id})
            MATCH (comp:Competition {wiki_id: row.competition_id})
            MERGE (cl)-[:COMPETES_IN]->(comp)
            """
            
            for i in tqdm(range(0, len(matched), self.batch_size), desc="Importing competes_in"):
                batch = matched[i:i + self.batch_size]
                self.run_batch(query, batch)
        
        logger.info(f"Imported {len(matched)} competes_in relationships")
    
    def import_same_province(self):
        """Import SAME_PROVINCE (derby/rivals) relationships (Club <-> Club)."""
        rows = self.load_csv("same_province.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            club1_id = self._safe_int(row.get("club1_id"))
            club2_id = self._safe_int(row.get("club2_id"))
            province_id = self._safe_int(row.get("province_id"))
            province_name = row.get("province_name", "")
            
            if club1_id is not None and club2_id is not None:
                valid_rows.append({
                    "club1_id": club1_id,
                    "club2_id": club2_id,
                    "province_id": province_id,
                    "province_name": province_name,
                })
        
        if not valid_rows:
            logger.warning("No valid same_province relationships to import")
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (c1:Club {wiki_id: row.club1_id})
        MATCH (c2:Club {wiki_id: row.club2_id})
        MERGE (c1)-[r:SAME_PROVINCE]-(c2)
        SET r.province_name = row.province_name
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing same_province"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} same_province (derby) relationships")
    
    def import_player_from_province(self):
        """Import PLAYER_FROM_PROVINCE relationships (Player -> Province)."""
        rows = self.load_csv("player_from_province.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            player_id = self._safe_int(row.get("player_id"))
            province_id = self._safe_int(row.get("province_id"))
            
            if player_id is not None and province_id is not None:
                valid_rows.append({
                    "player_id": player_id,
                    "province_id": province_id,
                })
        
        if not valid_rows:
            logger.warning("No valid player_from_province relationships to import")
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p:Player {wiki_id: row.player_id})
        MATCH (prov:Province {province_id: row.province_id})
        MERGE (p)-[:FROM_PROVINCE]->(prov)
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing player_from_province"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} player_from_province relationships")
    
    def import_played_same_club(self):
        """Import PLAYED_SAME_CLUB relationships (Player <-> Player who shared 2+ clubs)."""
        rows = self.load_csv("played_same_club.csv", EDGES_DATA_DIR)
        if not rows:
            return
        
        valid_rows = []
        for row in rows:
            player1_id = self._safe_int(row.get("player1_id"))
            player2_id = self._safe_int(row.get("player2_id"))
            shared_clubs_count = self._safe_int(row.get("shared_clubs_count"))
            shared_clubs = row.get("shared_clubs", "")
            
            if player1_id is not None and player2_id is not None:
                valid_rows.append({
                    "player1_id": player1_id,
                    "player2_id": player2_id,
                    "shared_clubs_count": shared_clubs_count or 0,
                    "shared_clubs": shared_clubs,
                })
        
        if not valid_rows:
            logger.warning("No valid played_same_club relationships to import")
            return
        
        query = """
        UNWIND $batch AS row
        MATCH (p1:Player {wiki_id: row.player1_id})
        MATCH (p2:Player {wiki_id: row.player2_id})
        MERGE (p1)-[r:PLAYED_SAME_CLUBS]-(p2)
        SET r.shared_clubs_count = row.shared_clubs_count,
            r.shared_clubs = row.shared_clubs
        """
        
        for i in tqdm(range(0, len(valid_rows), self.batch_size), desc="Importing played_same_club"):
            batch = valid_rows[i:i + self.batch_size]
            self.run_batch(query, batch)
        
        logger.info(f"Imported {len(valid_rows)} played_same_club relationships")

    def import_all(self, reset: bool = False):
        """
        Run the complete import process.
        
        Args:
            reset: Whether to drop all existing data first
        """
        if not self.connect():
            logger.error("Failed to connect to Neo4j. Aborting import.")
            return
        
        try:
            if reset:
                self.reset_database()
            
            # Create schema
            self.create_schema()
            
            # Import nodes
            logger.info("\n" + "=" * 60)
            logger.info("IMPORTING NODES")
            logger.info("=" * 60)
            
            # Position is now a property on Player, not imported separately
            self.import_provinces()
            self.import_players()
            self.import_coaches()
            self.import_clubs()
            self.import_national_teams()
            self.import_stadiums()
            self.import_competitions()
            
            # Import relationships
            logger.info("\n" + "=" * 60)
            logger.info("IMPORTING RELATIONSHIPS")
            logger.info("=" * 60)
            
            self.import_played_for()
            self.import_played_for_national()
            self.import_coached()
            self.import_teammate()
            self.import_national_teammate()
            self.import_under_coach()
            # HAS_POSITION relationship removed - position is now a Player property
            self.import_born_in()
            self.import_home_stadium()
            self.import_stadium_in_province()
            self.import_club_based_in()
            self.import_competes_in()
            self.import_same_province()
            self.import_player_from_province()
            self.import_played_same_club()
            
            # Print summary
            self._print_summary()
            
        finally:
            self.close()
    
    def _print_summary(self):
        """Print import summary."""
        print("\n" + "=" * 60)
        print("IMPORT SUMMARY")
        print("=" * 60)
        print(f"  Nodes created: {self.stats['nodes_created']}")
        print(f"  Relationships created: {self.stats['relationships_created']}")
        print(f"  Errors: {self.stats['errors']}")
        print("=" * 60)


def main():
    """Main entry point for the Neo4j import CLI."""
    parser = argparse.ArgumentParser(
        description="Import Vietnam Football Knowledge Graph data into Neo4j",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Import to Neo4j Aura:
    python -m neo4j_import.import_to_neo4j --uri neo4j+s://xxx.databases.neo4j.io --user neo4j --password yourpassword
    
  Import with reset (delete existing data first):
    python -m neo4j_import.import_to_neo4j --uri neo4j+s://xxx.databases.neo4j.io --user neo4j --password yourpassword --reset
    
  Use environment variables:
    export NEO4J_URI="neo4j+s://xxx.databases.neo4j.io"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="yourpassword"
    python -m neo4j_import.import_to_neo4j
        """,
    )
    
    parser.add_argument(
        "--uri",
        type=str,
        default=NEO4J_URI,
        help=f"Neo4j connection URI (default: from config or env)",
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
        "--reset",
        action="store_true",
        help="Drop all existing data before import",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of records per batch (default: 500)",
    )
    
    args = parser.parse_args()
    
    # Validate connection params
    if not args.uri or "xxx" in args.uri:
        print("Error: Please provide a valid Neo4j URI via --uri or NEO4J_URI environment variable")
        sys.exit(1)
    
    if not args.password or args.password == "your-password-here":
        print("Error: Please provide a Neo4j password via --password or NEO4J_PASSWORD environment variable")
        sys.exit(1)
    
    # Create importer and run
    importer = Neo4jImporter(
        uri=args.uri,
        user=args.user,
        password=args.password,
        batch_size=args.batch_size,
    )
    
    importer.import_all(reset=args.reset)


if __name__ == "__main__":
    main()
