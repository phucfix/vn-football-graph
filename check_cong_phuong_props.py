"""Find Công Phượng's Wikipedia URL from Neo4j"""
from chatbot.knowledge_graph import get_kg

kg = get_kg()

query = """
MATCH (p:Player {name: 'Nguyễn Công Phượng'})
RETURN p.name as name, p.wikipedia_url as url, p.birth_date as birth, 
       p.birth_place as birthplace, properties(p) as props
"""

result = kg.driver.execute_query(query)

print("=" * 60)
print("NGUYỄN CÔNG PHƯỢNG - PROPERTIES IN NEO4J")
print("=" * 60)

if result.records:
    record = result.records[0]
    print(f"\nName: {record['name']}")
    print(f"Wikipedia URL: {record['url']}")
    print(f"Birth Date: {record['birth']}")
    print(f"Birth Place: {record['birthplace']}")
    print(f"\nAll Properties:")
    for key, value in record['props'].items():
        print(f"   {key}: {value}")
else:
    print("❌ Not found!")

kg.close()
