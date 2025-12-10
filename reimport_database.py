#!/usr/bin/env python3
"""
Re-import toàn bộ database từ đầu

Xóa hết data cũ và import lại từ data/parsed để có database hoàn hảo
"""

import os
import sys
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

class DatabaseReimporter:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def close(self):
        self.driver.close()
    
    def get_current_stats(self):
        """Lấy thống kê hiện tại"""
        with self.driver.session() as session:
            nodes = session.run('MATCH (n) RETURN count(n) as count').single()['count']
            rels = session.run('MATCH ()-[r]->() RETURN count(r) as count').single()['count']
            return nodes, rels
    
    def drop_all_data(self):
        """Xóa toàn bộ data trong database"""
        logger.info("Dropping all data...")
        with self.driver.session() as session:
            # Drop constraints first (if any)
            result = session.run('SHOW CONSTRAINTS')
            constraints = [r['name'] for r in result]
            for constraint in constraints:
                try:
                    session.run(f'DROP CONSTRAINT {constraint} IF EXISTS')
                    logger.info(f"Dropped constraint: {constraint}")
                except:
                    pass
            
            # Drop all nodes and relationships
            session.run('MATCH (n) DETACH DELETE n')
            logger.info("All data deleted")
    
    def reimport_data(self):
        """Re-import data bằng cách chạy import script gốc"""
        logger.info("Re-importing data from parsed files...")
        
        # Import using the original script
        from neo4j_import.import_to_neo4j import main as import_main
        
        import_main()

def main():
    print("=" * 80)
    print("🔄 DATABASE RE-IMPORT")
    print("=" * 80)
    print()
    print("⚠️  WARNING: This will:")
    print("   1. DELETE all data in Neo4j database")
    print("   2. Re-import from data/parsed/ directory")
    print("   3. Restore to ORIGINAL clean state")
    print()
    
    reimporter = DatabaseReimporter()
    
    try:
        # Show current stats
        nodes, rels = reimporter.get_current_stats()
        print(f"📊 Current database:")
        print(f"   - Nodes: {nodes:,}")
        print(f"   - Relationships: {rels:,}")
        print()
        
        # Confirm
        confirm = input("❓ Proceed with re-import? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Cancelled")
            return
        
        print()
        print("=" * 80)
        print("STEP 1: Dropping all data...")
        print("=" * 80)
        reimporter.drop_all_data()
        
        print()
        print("=" * 80)
        print("STEP 2: Re-importing from parsed files...")
        print("=" * 80)
        reimporter.reimport_data()
        
        print()
        print("=" * 80)
        print("STEP 3: Verifying...")
        print("=" * 80)
        
        nodes, rels = reimporter.get_current_stats()
        print(f"\n📊 New database:")
        print(f"   - Nodes: {nodes:,}")
        print(f"   - Relationships: {rels:,}")
        
        print()
        print("=" * 80)
        print("✅ RE-IMPORT COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📌 Next steps:")
        print("   1. Verify data: check some sample queries")
        print("   2. Restart chatbot to reload cache")
        print("   3. Test chatbot accuracy")
        
    except Exception as e:
        logger.error(f"Error during re-import: {e}")
        print(f"\n❌ ERROR: {e}")
        print("\nDatabase may be in inconsistent state!")
        print("Please check logs and manually verify.")
        
    finally:
        reimporter.close()

if __name__ == '__main__':
    main()
