"""
Direct import of enriched relations to Neo4j using Python driver.
Bypasses DNS issues by using direct connection with retries.
"""

import json
import time
import socket
import logging
from pathlib import Path
from typing import List, Dict, Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / '.env')

NEO4J_URI = os.getenv('NEO4J_URI', 'neo4j+s://cdfeb4d9.databases.neo4j.io')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')


class DirectNeo4jImporter:
    """Import relations directly to Neo4j with retry logic."""
    
    def __init__(self, uri: str, user: str, password: str, max_retries: int = 5):
        self.uri = uri
        self.user = user
        self.password = password
        self.max_retries = max_retries
        self.driver = None
        
    def connect_with_retry(self) -> bool:
        """Connect to Neo4j with retry logic for DNS issues."""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Connection attempt {attempt}/{self.max_retries}...")
                
                # Try to resolve DNS first
                host = self.uri.replace("neo4j+s://", "").replace("bolt+s://", "").split(":")[0]
                logger.info(f"Resolving DNS for {host}...")
                socket.gethostbyname(host)
                logger.info("DNS resolved successfully")
                
                # Connect to Neo4j
                self.driver = GraphDatabase.driver(
                    self.uri, 
                    auth=(self.user, self.password),
                    max_connection_lifetime=3600,
                    connection_timeout=60
                )
                
                # Verify connection
                with self.driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    result.single()
                    
                logger.info("✓ Connected to Neo4j successfully!")
                return True
                
            except socket.gaierror as e:
                logger.warning(f"DNS resolution failed: {e}")
                if attempt < self.max_retries:
                    wait_time = attempt * 5  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
            except ServiceUnavailable as e:
                logger.warning(f"Neo4j service unavailable: {e}")
                if attempt < self.max_retries:
                    wait_time = attempt * 5
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Connection error: {e}")
                if attempt < self.max_retries:
                    wait_time = attempt * 3
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
        logger.error("Failed to connect after all retries")
        return False
    
    def close(self):
        """Close the driver connection."""
        if self.driver:
            self.driver.close()
            
    def import_relations(self, relations_file: Path, batch_size: int = 100) -> Dict[str, int]:
        """Import relations from JSONL file in batches."""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
            
        # Load relations
        relations = []
        with open(relations_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    relations.append(json.loads(line))
                    
        logger.info(f"Loaded {len(relations)} relations from {relations_file}")
        
        # Group by relation type and node labels
        type_mapping = {
            'PLAYER': 'Player',
            'CLUB': 'Club',
            'COMPETITION': 'Competition',
            'NATIONAL_TEAM': 'NationalTeam',
            'COACH': 'Coach',
            'STADIUM': 'Stadium'
        }
        
        grouped = {}
        for r in relations:
            pred = r['predicate']
            s_label = type_mapping.get(r['subject']['type'], 'Entity')
            o_label = type_mapping.get(r['object']['type'], 'Entity')
            key = (pred, s_label, o_label)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append({
                's_id': int(r['subject']['wiki_id']),
                'o_id': int(r['object']['wiki_id']),
                'conf': r['confidence'],
                'pattern': r['pattern']
            })
            
        # Import each group
        stats = {'total': 0, 'created': 0, 'matched': 0, 'errors': 0}
        
        for (pred, s_label, o_label), data in grouped.items():
            logger.info(f"Importing {pred}: {s_label} -> {o_label} ({len(data)} relations)")
            
            # Process in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                
                query = f"""
                UNWIND $batch AS row
                MATCH (s:{s_label} {{wiki_id: row.s_id}})
                MATCH (o:{o_label} {{wiki_id: row.o_id}})
                MERGE (s)-[r:{pred}]->(o)
                ON CREATE SET r.confidence = row.conf, 
                              r.pattern = row.pattern, 
                              r.source = 'enrichment', 
                              r.created_at = datetime()
                RETURN count(r) as count
                """
                
                try:
                    with self.driver.session() as session:
                        result = session.run(query, batch=batch)
                        record = result.single()
                        count = record['count'] if record else 0
                        stats['created'] += count
                        stats['total'] += len(batch)
                        
                except TransientError as e:
                    logger.warning(f"Transient error, retrying: {e}")
                    time.sleep(2)
                    try:
                        with self.driver.session() as session:
                            result = session.run(query, batch=batch)
                            record = result.single()
                            count = record['count'] if record else 0
                            stats['created'] += count
                            stats['total'] += len(batch)
                    except Exception as e:
                        logger.error(f"Failed after retry: {e}")
                        stats['errors'] += len(batch)
                except Exception as e:
                    logger.error(f"Error importing batch: {e}")
                    stats['errors'] += len(batch)
                    
            logger.info(f"  ✓ Completed {pred}")
            
        return stats
    
    def verify_import(self) -> int:
        """Verify the number of enrichment relations imported."""
        if not self.driver:
            return 0
            
        query = """
        MATCH ()-[r]->() 
        WHERE r.source = 'enrichment' 
        RETURN count(r) as count
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            record = result.single()
            return record['count'] if record else 0


def main():
    """Main function to import enriched relations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import enriched relations to Neo4j')
    parser.add_argument('--input', type=str, 
                        default=str(BASE_DIR / 'data' / 'enrichment' / 'matched_relations.jsonl'),
                        help='Input JSONL file with relations')
    parser.add_argument('--batch-size', type=int, default=50,
                        help='Batch size for import')
    parser.add_argument('--max-retries', type=int, default=10,
                        help='Max connection retries')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DIRECT IMPORT TO NEO4J")
    print("=" * 60)
    print(f"Input: {args.input}")
    print(f"Batch size: {args.batch_size}")
    print(f"Max retries: {args.max_retries}")
    print()
    
    # Create importer
    importer = DirectNeo4jImporter(
        NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
        max_retries=args.max_retries
    )
    
    try:
        # Connect with retry
        if not importer.connect_with_retry():
            print("\n❌ Could not connect to Neo4j after retries")
            print("Please check:")
            print("  1. Internet connection")
            print("  2. Neo4j credentials in config/config.py")
            print("  3. Neo4j instance is running")
            return 1
            
        # Import relations
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ Input file not found: {input_path}")
            return 1
            
        stats = importer.import_relations(input_path, batch_size=args.batch_size)
        
        print("\n" + "=" * 60)
        print("IMPORT RESULTS")
        print("=" * 60)
        print(f"Total relations processed: {stats['total']}")
        print(f"Relations created/matched: {stats['created']}")
        print(f"Errors: {stats['errors']}")
        
        # Verify
        count = importer.verify_import()
        print(f"\n✓ Total enrichment relations in database: {count}")
        
        return 0
        
    finally:
        importer.close()


if __name__ == '__main__':
    exit(main())
