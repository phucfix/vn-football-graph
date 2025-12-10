#!/usr/bin/env python3
"""
Cleanup Infobox Enrichment

Xóa tất cả relationships được tạo bởi infobox_enrichment.py
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class CleanupInfoboxEnrichment:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def close(self):
        self.driver.close()
    
    def count_enrichment_data(self):
        """Đếm relationships từ infobox_enrichment"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH ()-[r]->()
                WHERE r.source = 'infobox_enrichment'
                RETURN count(r) as count
            ''')
            return result.single()['count']
    
    def get_stats(self):
        """Thống kê chi tiết"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH ()-[r]->()
                WHERE r.source = 'infobox_enrichment'
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
            ''')
            return [(r['rel_type'], r['count']) for r in result]
    
    def delete_enrichment_data(self, batch_size=1000):
        """Xóa tất cả relationships từ infobox_enrichment"""
        total_deleted = 0
        
        with self.driver.session() as session:
            while True:
                result = session.run('''
                    MATCH ()-[r]->()
                    WHERE r.source = 'infobox_enrichment'
                    WITH r LIMIT $batch_size
                    DELETE r
                    RETURN count(r) as deleted
                ''', batch_size=batch_size)
                
                deleted = result.single()['deleted']
                total_deleted += deleted
                
                logger.info(f"Deleted {deleted} relationships (total: {total_deleted})")
                
                if deleted < batch_size:
                    break
        
        return total_deleted

def main():
    print("=" * 80)
    print("🧹 CLEANUP INFOBOX ENRICHMENT")
    print("=" * 80)
    print()
    print("⚠️  This will DELETE all relationships with source='infobox_enrichment'")
    print()
    
    cleanup = CleanupInfoboxEnrichment()
    
    try:
        # Count
        total = cleanup.count_enrichment_data()
        print(f"📊 Found {total} relationships from infobox_enrichment")
        
        if total == 0:
            print("✅ Nothing to delete")
            return
        
        # Show stats
        stats = cleanup.get_stats()
        print("\n📋 Breakdown:")
        for rel_type, count in stats:
            print(f"  - {rel_type}: {count}")
        
        # Confirm
        print()
        confirm = input("❓ Proceed with deletion? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Cancelled")
            return
        
        # Delete
        print("\n🗑️  Deleting...")
        deleted = cleanup.delete_enrichment_data()
        
        print()
        print("=" * 80)
        print("✅ CLEANUP COMPLETED!")
        print("=" * 80)
        print(f"  Deleted: {deleted} relationships")
        
    finally:
        cleanup.close()

if __name__ == '__main__':
    main()
