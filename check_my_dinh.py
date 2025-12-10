"""Check Mỹ Đình stadium data"""
from chatbot.knowledge_graph import get_kg

kg = get_kg()

print("=" * 60)
print("CHECKING MỸ ĐÌNH STADIUM")
print("=" * 60)

# Search for Mỹ Đình
query1 = """
MATCH (s)
WHERE s.name CONTAINS 'Mỹ Đình' OR s.name CONTAINS 'My Dinh'
RETURN s.name as name, labels(s) as labels, properties(s) as props
"""

result = kg.driver.execute_query(query1)

if result.records:
    print(f"\n✅ Found {len(result.records)} entities with 'Mỹ Đình':")
    for record in result.records:
        print(f"\n   Name: {record['name']}")
        print(f"   Labels: {record['labels']}")
        print(f"   Properties:")
        for key, value in record['props'].items():
            if key not in ['name']:
                print(f"      {key}: {value}")
else:
    print("❌ No entities found with 'Mỹ Đình'")

# Check location relationship
print("\n" + "=" * 60)
print("MỸ ĐÌNH LOCATION RELATIONSHIP")
print("=" * 60)

query2 = """
MATCH (s {name: 'Sân vận động Quốc gia Mỹ Đình'})-[r:LOCATED_IN]->(location)
RETURN location.name as location, labels(location) as labels
"""

result = kg.driver.execute_query(query2)

if result.records:
    print(f"\n✅ Found location:")
    for record in result.records:
        print(f"   Sân Mỹ Đình -[LOCATED_IN]-> {record['location']} {record['labels']}")
else:
    print("❌ No LOCATED_IN relationship found")
    
    # Try other relationship types
    query3 = """
    MATCH (s {name: 'Sân vận động Quốc gia Mỹ Đình'})-[r]->(target)
    RETURN type(r) as rel_type, target.name as target_name, labels(target) as labels
    LIMIT 10
    """
    
    result = kg.driver.execute_query(query3)
    
    if result.records:
        print("\n📊 Other relationships found:")
        for record in result.records:
            print(f"   -{record['rel_type']}-> {record['target_name']} {record['labels']}")
    else:
        print("❌ No relationships at all!")

kg.close()
