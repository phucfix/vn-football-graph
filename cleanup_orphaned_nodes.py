#!/usr/bin/env python3
"""
Delete orphaned nodes created by enrichment

Xóa clubs và national teams không có wiki_id (được tạo bởi MERGE trong enrichment)
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class CleanupOrphanedNodes:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def close(self):
        self.driver.close()
    
    def count_orphaned_clubs(self):
        """Count clubs without wiki_id"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (c:Club)
                WHERE c.wiki_id IS NULL
                RETURN count(c) as count
            ''')
            return result.single()['count']
    
    def count_orphaned_national_teams(self):
        """Count national teams without wiki_id"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (nt:NationalTeam)
                WHERE nt.wiki_id IS NULL
                RETURN count(nt) as count
            ''')
            return result.single()['count']
    
    def get_sample_clubs(self, limit=20):
        """Get sample clubs without wiki_id"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (c:Club)
                WHERE c.wiki_id IS NULL
                RETURN c.name as name
                LIMIT $limit
            ''', limit=limit)
            return [r['name'] for r in result]
    
    def get_sample_teams(self, limit=20):
        """Get sample national teams without wiki_id"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (nt:NationalTeam)
                WHERE nt.wiki_id IS NULL
                RETURN nt.name as name
                LIMIT $limit
            ''', limit=limit)
            return [r['name'] for r in result]
    
    def delete_orphaned_clubs(self):
        """Delete clubs without wiki_id"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (c:Club)
                WHERE c.wiki_id IS NULL
                DETACH DELETE c
                RETURN count(c) as deleted
            ''')
            return result.single()['deleted']
    
    def delete_orphaned_national_teams(self):
        """Delete national teams without wiki_id"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (nt:NationalTeam)
                WHERE nt.wiki_id IS NULL
                DETACH DELETE nt
                RETURN count(nt) as deleted
            ''')
            return result.single()['deleted']

def main():
    print("=" * 80)
    print("🧹 CLEANUP ORPHANED NODES")
    print("=" * 80)
    print()
    print("⚠️  This will DELETE:")
    print("   - Clubs WITHOUT wiki_id (created by enrichment MERGE)")
    print("   - National Teams WITHOUT wiki_id (created by enrichment MERGE)")
    print()
    
    cleanup = CleanupOrphanedNodes()
    
    try:
        # Count
        clubs_count = cleanup.count_orphaned_clubs()
        teams_count = cleanup.count_orphaned_national_teams()
        
        print(f"📊 Found:")
        print(f"  - {clubs_count} orphaned clubs")
        print(f"  - {teams_count} orphaned national teams")
        print(f"  - TOTAL: {clubs_count + teams_count} nodes")
        
        if clubs_count == 0 and teams_count == 0:
            print("\n✅ Nothing to delete")
            return
        
        # Show samples
        if clubs_count > 0:
            samples = cleanup.get_sample_clubs(10)
            print(f"\n📋 Sample clubs (first 10):")
            for name in samples:
                print(f"  - {name}")
        
        if teams_count > 0:
            samples = cleanup.get_sample_teams(10)
            print(f"\n📋 Sample national teams (first 10):")
            for name in samples:
                print(f"  - {name}")
        
        # Confirm
        print()
        confirm = input("❓ Proceed with deletion? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Cancelled")
            return
        
        # Delete
        print("\n🗑️  Deleting...")
        
        clubs_deleted = cleanup.delete_orphaned_clubs()
        logger.info(f"Deleted {clubs_deleted} clubs")
        
        teams_deleted = cleanup.delete_orphaned_national_teams()
        logger.info(f"Deleted {teams_deleted} national teams")
        
        print()
        print("=" * 80)
        print("✅ CLEANUP COMPLETED!")
        print("=" * 80)
        print(f"  Clubs deleted: {clubs_deleted}")
        print(f"  National teams deleted: {teams_deleted}")
        print(f"  Total nodes deleted: {clubs_deleted + teams_deleted}")
        
    finally:
        cleanup.close()

if __name__ == '__main__':
    main()
