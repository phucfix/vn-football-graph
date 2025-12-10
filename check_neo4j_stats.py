#!/usr/bin/env python3
"""
Script kiểm tra thống kê toàn bộ mạng Neo4j.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


class Neo4jStats:
    """Class để lấy thống kê Neo4j."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
    
    def close(self):
        self.driver.close()
    
    def get_node_counts(self):
        """Đếm số lượng nodes theo label."""
        with self.driver.session() as session:
            # Get all labels
            labels_result = session.run("CALL db.labels()")
            labels = [r['label'] for r in labels_result]
            
            # Count nodes for each label
            counts = []
            for label in labels:
                result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
                count = result.single()['count']
                counts.append((label, count))
            
            return sorted(counts, key=lambda x: x[1], reverse=True)
    
    def get_relationship_counts(self):
        """Đếm số lượng relationships theo type."""
        with self.driver.session() as session:
            # Get all relationship types
            types_result = session.run("CALL db.relationshipTypes()")
            rel_types = [r['relationshipType'] for r in types_result]
            
            # Count relationships for each type
            counts = []
            for rel_type in rel_types:
                result = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count")
                count = result.single()['count']
                counts.append((rel_type, count))
            
            return sorted(counts, key=lambda x: x[1], reverse=True)
    
    def get_relationship_sources(self):
        """Đếm relationships theo source."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH ()-[r]->()
                WHERE r.source IS NOT NULL
                RETURN r.source as source, count(r) as count
                ORDER BY count DESC
            """)
            return [(r['source'], r['count']) for r in result]
    
    def get_sample_players(self, limit=10):
        """Lấy sample players."""
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (p:Player)
                RETURN p.name as name, p.wiki_id as wiki_id
                LIMIT {limit}
            """)
            return [(r['name'], r['wiki_id']) for r in result]
    
    def check_cong_phuong(self):
        """Kiểm tra Công Phượng cụ thể."""
        with self.driver.session() as session:
            # Check player node
            result1 = session.run("""
                MATCH (p:Player)
                WHERE p.name CONTAINS 'Công Phượng'
                RETURN p.name, p.wiki_id, p.birth_date
            """)
            players = list(result1)
            
            # Check PLAYED_FOR relationships
            result2 = session.run("""
                MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club)
                WHERE p.name CONTAINS 'Công Phượng'
                RETURN p.name, c.name, r.source
            """)
            clubs = list(result2)
            
            return players, clubs


def main():
    print("=" * 80)
    print("📊 NEO4J DATABASE STATISTICS")
    print("=" * 80)
    print()
    
    stats = Neo4jStats()
    
    try:
        # Node counts
        print("📦 NODE COUNTS BY LABEL:")
        print("-" * 80)
        node_counts = stats.get_node_counts()
        total_nodes = sum(count for _, count in node_counts)
        
        for label, count in node_counts:
            print(f"  {label:30} {count:>8,}")
        print(f"  {'TOTAL':30} {total_nodes:>8,}")
        print()
        
        # Relationship counts
        print("🔗 RELATIONSHIP COUNTS BY TYPE:")
        print("-" * 80)
        rel_counts = stats.get_relationship_counts()
        total_rels = sum(count for _, count in rel_counts)
        
        for rel_type, count in rel_counts:
            print(f"  {rel_type:30} {count:>8,}")
        print(f"  {'TOTAL':30} {total_rels:>8,}")
        print()
        
        # Relationship sources
        print("📝 RELATIONSHIP COUNTS BY SOURCE:")
        print("-" * 80)
        sources = stats.get_relationship_sources()
        for source, count in sources:
            print(f"  {source:30} {count:>8,}")
        print()
        
        # Sample players
        print("👤 SAMPLE PLAYERS (first 10):")
        print("-" * 80)
        players = stats.get_sample_players(10)
        for name, wiki_id in players:
            print(f"  {name:40} (wiki_id: {wiki_id})")
        print()
        
        # Check Công Phượng specifically
        print("🔍 CHECKING CÔNG PHƯỢNG:")
        print("-" * 80)
        cp_players, cp_clubs = stats.check_cong_phuong()
        
        if cp_players:
            print(f"  Found {len(cp_players)} player(s):")
            for record in cp_players:
                print(f"    - {record['p.name']} (wiki_id: {record['p.wiki_id']})")
        else:
            print("  ❌ No player found with 'Công Phượng' in name")
        
        print()
        if cp_clubs:
            print(f"  PLAYED_FOR relationships: {len(cp_clubs)}")
            for record in cp_clubs[:10]:  # First 10
                print(f"    - {record['c.name']} (source: {record['r.source']})")
            if len(cp_clubs) > 10:
                print(f"    ... and {len(cp_clubs) - 10} more")
        else:
            print("  ❌ No PLAYED_FOR relationships found")
        
        print()
        print("=" * 80)
        print("✅ DATABASE CHECK COMPLETED")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stats.close()


if __name__ == "__main__":
    main()
