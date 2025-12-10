#!/usr/bin/env python3
"""
Cleanup Enrichment Nodes from Neo4j

Xóa tất cả nodes được tạo từ text_extraction/enrichment.
Giữ lại chỉ nodes từ Wikipedia infobox parsing.
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

class EnrichmentNodeCleanup:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def close(self):
        self.driver.close()
    
    def count_enrichment_nodes(self):
        """Đếm số nodes từ enrichment"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (n)
                WHERE n.source = 'text_extraction' OR n.source = 'enrichment'
                RETURN count(n) as total
            ''')
            return result.single()['total']
    
    def get_enrichment_stats(self):
        """Thống kê chi tiết nodes từ enrichment"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (n)
                WHERE n.source = 'text_extraction' OR n.source = 'enrichment'
                RETURN labels(n)[0] as label, n.source as source, count(*) as count
                ORDER BY count DESC
            ''')
            return [(r['label'], r['source'], r['count']) for r in result]
    
    def get_sample_nodes(self, limit=20):
        """Lấy sample nodes để xem"""
        with self.driver.session() as session:
            result = session.run('''
                MATCH (n)
                WHERE n.source = 'text_extraction' OR n.source = 'enrichment'
                RETURN labels(n)[0] as label, 
                       coalesce(n.name, n.title, id(n)) as name,
                       n.source as source
                LIMIT $limit
            ''', limit=limit)
            return [(r['label'], r['name'], r['source']) for r in result]
    
    def delete_enrichment_nodes(self, batch_size=1000):
        """
        Xóa nodes từ enrichment.
        
        NOTE: Neo4j sẽ tự động xóa relationships kết nối với nodes này.
        """
        total_deleted = 0
        
        with self.driver.session() as session:
            while True:
                result = session.run('''
                    MATCH (n)
                    WHERE n.source = 'text_extraction' OR n.source = 'enrichment'
                    WITH n LIMIT $batch_size
                    DETACH DELETE n
                    RETURN count(n) as deleted
                ''', batch_size=batch_size)
                
                deleted = result.single()['deleted']
                total_deleted += deleted
                
                logger.info(f"Deleted {deleted} nodes (total: {total_deleted})")
                
                if deleted < batch_size:
                    break
        
        return total_deleted
    
    def verify_cleanup(self):
        """Verify không còn enrichment nodes"""
        count = self.count_enrichment_nodes()
        if count == 0:
            logger.info("✅ Verification PASSED: No enrichment nodes remaining")
            return True
        else:
            logger.error(f"❌ Verification FAILED: Still {count} enrichment nodes")
            return False

def main():
    print("=" * 80)
    print("🧹 NEO4J ENRICHMENT NODES CLEANUP TOOL")
    print("=" * 80)
    print()
    print("⚠️  WARNING: This will DELETE all nodes with source='text_extraction' or 'enrichment'")
    print("   This includes:")
    print("   - Entity nodes (dates, wrong extractions)")
    print("   - Player/Club/Province nodes created by enrichment")
    print("   - All relationships connected to these nodes (DETACH DELETE)")
    print()
    
    cleanup = EnrichmentNodeCleanup()
    
    try:
        # Show current stats
        print("📊 Current statistics:")
        print("-" * 80)
        total = cleanup.count_enrichment_nodes()
        print(f"Total enrichment nodes: {total}")
        print()
        
        if total > 0:
            print("Breakdown by label:")
            stats = cleanup.get_enrichment_stats()
            for label, source, count in stats:
                print(f"  - {label}: {count} nodes (source: {source})")
            print()
            
            print("Sample nodes (first 20):")
            samples = cleanup.get_sample_nodes(20)
            for label, name, source in samples:
                print(f"  - {label}: {name} (source: {source})")
            print()
        
        # Ask for confirmation
        confirm = input("❓ Proceed with deletion? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Cancelled by user")
            return
        
        print()
        print("🗑️  Deleting enrichment nodes (DETACH DELETE)...")
        print("-" * 80)
        
        deleted = cleanup.delete_enrichment_nodes()
        
        print()
        print("🔍 Verifying cleanup...")
        print("-" * 80)
        cleanup.verify_cleanup()
        
        print()
        print("=" * 80)
        print("✅ CLEANUP COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📌 Summary:")
        print(f"   - Deleted {deleted} enrichment nodes")
        print(f"   - All connected relationships also deleted (DETACH DELETE)")
        print()
        print("📌 Next steps:")
        print("   1. Check node count: MATCH (n) RETURN labels(n), count(*)")
        print("   2. Restart chatbot to reload cache")
        print("   3. Verify data quality improved")
        
    finally:
        cleanup.close()

if __name__ == '__main__':
    main()
