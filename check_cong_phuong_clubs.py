"""Check Công Phượng's club relationships"""
from chatbot.knowledge_graph import get_kg

kg = get_kg()

print("=" * 60)
print("CÔNG PHƯỢNG CLUB RELATIONSHIPS")
print("=" * 60)

query = """
MATCH (p:Player {name: 'Nguyễn Công Phượng'})-[r:PLAYED_FOR]->(c)
RETURN c.name as club_name, labels(c) as labels
"""
result = kg.driver.execute_query(query)

if result.records:
    print(f"\n✅ Công Phượng PLAYED_FOR:")
    for record in result.records:
        print(f"   - {record['club_name']} {record['labels']}")
else:
    print("\n❌ NO PLAYED_FOR relationships found!")
    
# Try all relationships
query2 = """
MATCH (p:Player {name: 'Nguyễn Công Phươn g'})-[r]->(target)
WHERE target:Club OR target:Team
RETURN type(r) as rel_type, target.name as target_name, labels(target) as labels
"""
result2 = kg.driver.execute_query(query2)
if result2.records:
    print(f"\n📊 All club/team relationships:")
    for record in result2.records:
        print(f"   -{record['rel_type']}-> {record['target_name']} {record['labels']}")

kg.close()
