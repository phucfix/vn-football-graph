#!/usr/bin/env python3
"""
Debug script to investigate why chatbot fails on certain queries
"""

from chatbot.chatbot import SimpleChatbot
from chatbot.knowledge_graph import KnowledgeGraph

def main():
    print("="*80)
    print("DEBUGGING CHATBOT FAILURES")
    print("="*80)
    
    # Initialize
    kg = KnowledgeGraph()
    kg.connect()
    
    print("\n1. Checking entities in database...")
    print("-"*80)
    
    # Check for player names
    players_to_check = [
        "Công Phượng",
        "Nguyễn Công Phượng",
        "Văn Toàn",
        "Nguyễn Văn Toàn",
        "Quang Hải",
        "Nguyễn Quang Hải",
        "Tuấn Anh",
        "Lương Xuân Trường"
    ]
    
    for player in players_to_check:
        entity = kg.get_entity_by_name(player)
        if entity:
            print(f"✅ Found: {player} -> {entity.name} ({entity.label})")
        else:
            print(f"❌ NOT FOUND: {player}")
    
    print("\n2. Checking clubs...")
    print("-"*80)
    
    clubs_to_check = [
        "HAGL",
        "Hoàng Anh Gia Lai",
        "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
        "Hà Nội",
        "Hà Nội FC",
        "CLB Hà Nội"
    ]
    
    for club in clubs_to_check:
        entity = kg.get_entity_by_name(club)
        if entity:
            print(f"✅ Found: {club} -> {entity.name} ({entity.label})")
        else:
            print(f"❌ NOT FOUND: {club}")
    
    print("\n3. Checking relationships: Công Phượng - HAGL...")
    print("-"*80)
    
    # Try different name variations
    variations = [
        ("Công Phượng", "HAGL"),
        ("Nguyễn Công Phượng", "HAGL"),
        ("Công Phượng", "Hoàng Anh Gia Lai"),
        ("Nguyễn Công Phượng", "Hoàng Anh Gia Lai"),
        ("Công Phượng", "Câu lạc bộ bóng đá Hoàng Anh Gia Lai"),
        ("Nguyễn Công Phượng", "Câu lạc bộ bóng đá Hoàng Anh Gia Lai"),
    ]
    
    for player, club in variations:
        # Use cypher query to check
        query = """
        MATCH (p {name: $player})-[r:PLAYED_FOR]->(c {name: $club})
        RETURN count(r) > 0 as result
        """
        with kg.driver.session() as session:
            result = session.run(query, player=player, club=club)
            record = result.single()
            found = record["result"] if record else False
            print(f"  {player} -> {club}: {found}")
    
    print("\n4. Getting all relationships for Công Phượng...")
    print("-"*80)
    
    for name in ["Công Phượng", "Nguyễn Công Phượng"]:
        rels = kg.get_entity_relationships(name)
        if rels:
            print(f"\n{name} has {len(rels)} relationships:")
            for rel in rels[:10]:  # Show first 10
                print(f"  - {rel}")
        else:
            print(f"{name}: No relationships found")
    
    print("\n5. Checking Văn Toàn...")
    print("-"*80)
    
    for name in ["Văn Toàn", "Nguyễn Văn Toàn"]:
        entity = kg.get_entity_by_name(name)
        if entity:
            print(f"\n✅ Found: {name}")
            print(f"   Full name: {entity.name}")
            print(f"   Label: {entity.label}")
            print(f"   Properties: {entity.properties}")
            
            rels = kg.get_entity_relationships(name)
            print(f"   Relationships: {len(rels)}")
            for rel in rels[:5]:
                print(f"     - {rel}")
        else:
            print(f"❌ NOT FOUND: {name}")
    
    print("\n6. Searching for partial matches...")
    print("-"*80)
    
    # Try Cypher query to find all players with "Công Phượng" in name
    query = """
    MATCH (n)
    WHERE toLower(n.name) CONTAINS 'công phượng'
    RETURN n.name, labels(n), n
    LIMIT 10
    """
    
    with kg.driver.session() as session:
        result = session.run(query)
        records = list(result)
        print(f"\nNodes containing 'công phượng': {len(records)}")
        for record in records:
            print(f"  - {record['n.name']} ({record['labels(n)']})")
    
    # Try for Văn Toàn
    query = """
    MATCH (n)
    WHERE toLower(n.name) CONTAINS 'văn toàn'
    RETURN n.name, labels(n)
    LIMIT 10
    """
    
    with kg.driver.session() as session:
        result = session.run(query)
        records = list(result)
        print(f"\nNodes containing 'văn toàn': {len(records)}")
        for record in records:
            print(f"  - {record['n.name']} ({record['labels(n)']})")
    
    # Try for HAGL
    query = """
    MATCH (n)
    WHERE toLower(n.name) CONTAINS 'hagl' OR toLower(n.name) CONTAINS 'hoàng anh gia lai'
    RETURN n.name, labels(n)
    LIMIT 10
    """
    
    with kg.driver.session() as session:
        result = session.run(query)
        records = list(result)
        print(f"\nNodes containing 'HAGL' or 'Hoàng Anh Gia Lai': {len(records)}")
        for record in records:
            print(f"  - {record['n.name']} ({record['labels(n)']})")
    
    kg.close()
    
    print("\n" + "="*80)
    print("Debug completed!")
    print("="*80)


if __name__ == "__main__":
    main()
