#!/usr/bin/env python3
"""
Script để xóa toàn bộ dữ liệu từ text_extraction (NLP enrichment) khỏi Neo4j.

Lý do: Text extraction có nhiều lỗi, ví dụ Công Phượng bị match với 41 CLB!
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


class Neo4jCleaner:
    """Cleaner để xóa dữ liệu text_extraction từ Neo4j."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
    def close(self):
        self.driver.close()
    
    def count_text_extraction_relationships(self):
        """Đếm số lượng relationships từ text_extraction."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH ()-[r]->()
                WHERE r.source = 'text_extraction'
                RETURN count(r) as count
            """)
            return result.single()['count']
    
    def get_text_extraction_stats(self):
        """Lấy thống kê chi tiết về dữ liệu text_extraction."""
        with self.driver.session() as session:
            # Count by relationship type
            result = session.run("""
                MATCH ()-[r]->()
                WHERE r.source = 'text_extraction'
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
            """)
            stats = {}
            for record in result:
                stats[record['rel_type']] = record['count']
            return stats
    
    def delete_text_extraction_relationships(self, batch_size=1000):
        """
        Xóa toàn bộ relationships có source = 'text_extraction'.
        
        Args:
            batch_size: Số lượng relationships xóa mỗi batch (tránh timeout)
        """
        logger.info("Starting deletion of text_extraction relationships...")
        
        with self.driver.session() as session:
            total_deleted = 0
            
            while True:
                result = session.run(f"""
                    MATCH ()-[r]->()
                    WHERE r.source = 'text_extraction'
                    WITH r LIMIT {batch_size}
                    DELETE r
                    RETURN count(r) as deleted
                """)
                
                deleted = result.single()['deleted']
                total_deleted += deleted
                
                if deleted > 0:
                    logger.info(f"Deleted {deleted} relationships (total: {total_deleted})")
                else:
                    break
            
            logger.info(f"✅ Completed! Total deleted: {total_deleted}")
            return total_deleted
    
    def verify_cleanup(self):
        """Kiểm tra xem đã xóa hết chưa."""
        count = self.count_text_extraction_relationships()
        if count == 0:
            logger.info("✅ Verification PASSED: No text_extraction relationships remaining")
            return True
        else:
            logger.warning(f"⚠️ Verification FAILED: {count} text_extraction relationships still exist")
            return False


def main():
    print("=" * 80)
    print("🧹 NEO4J TEXT_EXTRACTION CLEANUP TOOL")
    print("=" * 80)
    print()
    print("⚠️  WARNING: This will DELETE all relationships with source='text_extraction'")
    print("   Reason: Text extraction has many errors (e.g., Công Phượng matched to 41 clubs)")
    print()
    
    cleaner = Neo4jCleaner()
    
    try:
        # Get stats
        print("📊 Current statistics:")
        print("-" * 80)
        total = cleaner.count_text_extraction_relationships()
        print(f"Total text_extraction relationships: {total:,}")
        print()
        
        if total == 0:
            print("✅ No text_extraction data found. Nothing to delete!")
            return
        
        stats = cleaner.get_text_extraction_stats()
        print("Breakdown by relationship type:")
        for rel_type, count in stats.items():
            print(f"  - {rel_type}: {count:,}")
        print()
        
        # Confirm deletion
        response = input("❓ Proceed with deletion? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("❌ Deletion cancelled by user.")
            return
        
        print()
        print("🗑️  Deleting text_extraction relationships...")
        print("-" * 80)
        
        deleted = cleaner.delete_text_extraction_relationships(batch_size=1000)
        
        print()
        print("🔍 Verifying cleanup...")
        print("-" * 80)
        cleaner.verify_cleanup()
        
        print()
        print("=" * 80)
        print("✅ CLEANUP COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📌 Next steps:")
        print("   1. Restart your chatbot to reload cache")
        print("   2. Test with: 'Công Phượng chơi cho đội nào? | Hà Nội | HAGL | Viettel'")
        print("   3. Verify Công Phượng now has correct clubs (should be ~5, not 41)")
        print()
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        raise
    finally:
        cleaner.close()


if __name__ == "__main__":
    main()
