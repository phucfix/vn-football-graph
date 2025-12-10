"""Check if ANY player has PLAYED_FOR relationships"""
from chatbot.knowledge_graph import get_kg

kg = get_kg()

print("=" * 60)
print("CHECKING PLAYED_FOR RELATIONSHIPS IN DATABASE")
print("=" * 60)

# Count PLAYED_FOR relationships
query = """
MATCH (p:Player)-[r:PLAYED_FOR]->(c)
RETURN count(r) as count
"""
result = kg.driver.execute_query(query)
count = result.records[0]['count'] if result.records else 0
print(f"\n📊 Total PLAYED_FOR relationships: {count}")

if count > 0:
    # Show some examples
    query2 = """
    MATCH (p:Player)-[r:PLAYED_FOR]->(c)
    RETURN p.name as player, c.name as club
    LIMIT 10
    """
    result2 = kg.driver.execute_query(query2)
    print(f"\n✅ Examples:")
    for record in result2.records:
        print(f"   {record['player']} -> {record['club']}")
else:
    print("\n❌ NO PLAYED_FOR relationships exist in database!")
    print("\n🔍 Checking what relationship types exist...")
    
    query3 = """
    MATCH (p:Player)-[r]->(target)
    RETURN DISTINCT type(r) as rel_type, count(r) as count
    ORDER BY count DESC
    LIMIT 10
    """
    result3 = kg.driver.execute_query(query3)
    print("\nTop relationship types from Players:")
    for record in result3.records:
        print(f"   {record['rel_type']}: {record['count']}")

kg.close()
