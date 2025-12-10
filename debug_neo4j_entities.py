"""
Debug script to check actual entity names in Neo4j database
"""
from chatbot.knowledge_graph import get_kg

def check_entities():
    kg = get_kg()
    
    print("=" * 60)
    print("CHECKING NEO4J ENTITY NAMES")
    print("=" * 60)
    
    # Test cases from failures
    test_queries = [
        ("Công Phượng", "Player"),
        ("Nguyễn Công Phượng", "Player"),
        ("Quang Hải", "Player"),
        ("Nguyễn Quang Hải", "Player"),
        ("Văn Toàn", "Player"),
        ("HAGL", "Club"),
        ("Hoàng Anh Gia Lai", "Club"),
        ("Học viện Bóng đáHoàng Anh Gia Lai", "Club"),
        ("Hà Nội", "Club"),
        ("Câu lạc bộ bóng đá Hà Nội", "Club"),
        ("Hà Nội FC", "Club"),
        ("Park Hang-seo", "Coach"),
        ("Mỹ Đình", "Stadium"),
        ("Sân vận động Quốc gia Mỹ Đình", "Stadium"),
    ]
    
    for query, entity_type in test_queries:
        print(f"\n🔍 Searching for: '{query}' (type: {entity_type})")
        
        # Try exact match
        entity = kg.get_entity_by_name(query)
        if entity:
            entity_type = getattr(entity, 'type', getattr(entity, 'entity_type', 'Unknown'))
            print(f"   ✅ EXACT MATCH: {entity.name} ({entity_type})")
        else:
            print(f"   ❌ No exact match")
        
        # Try fuzzy search
        results = kg.search_entities(query, limit=5)
        if results:
            print(f"   📊 Fuzzy search found {len(results)} results:")
            for i, result in enumerate(results[:3], 1):
                result_type = getattr(result, 'type', getattr(result, 'entity_type', 'Unknown'))
                print(f"      {i}. {result.name} ({result_type})")
        else:
            print(f"   ❌ No fuzzy matches")
    
    # Get all players
    print("\n" + "=" * 60)
    print("TOP 10 PLAYERS IN DATABASE")
    print("=" * 60)
    query = """
    MATCH (p:Player)
    RETURN p.name as name
    ORDER BY p.name
    LIMIT 10
    """
    result = kg.driver.execute_query(query)
    for record in result.records:
        print(f"  - {record['name']}")
    
    # Get all clubs
    print("\n" + "=" * 60)
    print("ALL CLUBS IN DATABASE")
    print("=" * 60)
    query = """
    MATCH (c:Club)
    RETURN c.name as name
    ORDER BY c.name
    """
    result = kg.driver.execute_query(query)
    for record in result.records:
        print(f"  - {record['name']}")
    
    # Check Công Phượng relationships
    print("\n" + "=" * 60)
    print("CÔNG PHƯỢNG RELATIONSHIPS (if found)")
    print("=" * 60)
    
    # Try multiple name variations
    for name_variant in ["Công Phượng", "Nguyễn Công Phượng", "Nguyen Cong Phuong"]:
        query = """
        MATCH (p:Player {name: $name})-[r]->(target)
        RETURN type(r) as rel_type, target.name as target_name
        LIMIT 10
        """
        result = kg.driver.execute_query(query, name=name_variant)
        if result.records:
            print(f"\n   ✅ Found with name: '{name_variant}'")
            for record in result.records:
                print(f"      -{record['rel_type']}-> {record['target_name']}")
            break
    else:
        print("   ❌ No relationships found for any name variant")
    
    # Check if HAGL exists
    print("\n" + "=" * 60)
    print("HAGL/HOÀNG ANH GIA LAI CHECK")
    print("=" * 60)
    
    hagl_variants = [
        "HAGL",
        "Hoàng Anh Gia Lai", 
        "Học viện Bóng đáHoàng Anh Gia Lai",
        "Câu lạc bộ bóng đá Hoàng Anh Gia Lai"
    ]
    
    for variant in hagl_variants:
        query = """
        MATCH (c:Club {name: $name})
        RETURN c.name as name, labels(c) as labels
        """
        result = kg.driver.execute_query(query, name=variant)
        if result.records:
            record = result.records[0]
            print(f"   ✅ Found: '{variant}' -> {record['name']} {record['labels']}")
        else:
            print(f"   ❌ Not found: '{variant}'")
    
    kg.close()

if __name__ == "__main__":
    check_entities()
