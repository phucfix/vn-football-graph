"""Search for Công Phương and HAGL connection"""
from chatbot.knowledge_graph import get_kg

kg = get_kg()

print("=" * 60)
print("SEARCHING FOR CÔNG PHƯỢNG <-> HAGL CONNECTION")
print("=" * 60)

# Check any connection between Công Phượng and HAGL clubs
hagl_names = [
    "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
    "Học viện Bóng đáHoàng Anh Gia Lai"
]

for hagl in hagl_names:
    print(f"\n🔍 Checking: {hagl}")
    query = """
    MATCH (p:Player {name: 'Nguyễn Công Phượng'})-[r]-(c {name: $club_name})
    RETURN type(r) as rel_type, c.name as club_name
    """
    result = kg.driver.execute_query(query, club_name=hagl)
    if result.records:
        print(f"   ✅ Found relationship:")
        for record in result.records:
            print(f"      {record['rel_type']} <-> {record['club_name']}")
    else:
        print(f"   ❌ No relationship found")

# Search for any players WITH PLAYED_FOR to HAGL
print("\n" + "=" * 60)
print("WHO PLAYED FOR HAGL?")
print("=" * 60)

for hagl in hagl_names:
    print(f"\n📋 Players who PLAYED_FOR {hagl}:")
    query = """
    MATCH (p:Player)-[r:PLAYED_FOR]->(c {name: $club_name})
    RETURN p.name as player
    LIMIT 20
    """
    result = kg.driver.execute_query(query, club_name=hagl)
    if result.records:
        for record in result.records:
            print(f"   - {record['player']}")
    else:
        print(f"   ❌ No players found")

kg.close()
