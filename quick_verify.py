"""Quick verification of fix"""
from chatbot.knowledge_graph import get_kg

kg = get_kg()

print("=" * 60)
print("VERIFY: Công Phượng PLAYED_FOR")
print("=" * 60)

query = """
MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club)
WHERE p.name CONTAINS 'Công Phượng' OR p.name CONTAINS 'Quang Hải'
RETURN p.name as player, c.name as club
ORDER BY player, club
"""

result = kg.driver.execute_query(query)

if result.records:
    for record in result.records:
        print(f"✅ {record['player']} -[PLAYED_FOR]-> {record['club']}")
else:
    print("❌ No results")

kg.close()
