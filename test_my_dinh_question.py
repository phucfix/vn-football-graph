"""Test Mỹ Đình question"""
from chatbot.chatbot import HybridChatbot

print("=" * 60)
print("TESTING: Sân Mỹ Đình ở đâu?")
print("=" * 60)

chatbot = HybridChatbot()

question = "Sân Mỹ Đình ở đâu?"

# Test answer
print(f"\nAsking: {question}")
response = chatbot.chat(question)
print(f"\n💬 Response: {response}")

# Check what the graph returns
from chatbot.knowledge_graph import get_kg
kg = get_kg()

print("\n" + "=" * 60)
print("DIRECT QUERY TEST")
print("=" * 60)

# Test if entity mapping works
from chatbot.entity_mapping import normalize_entity_name
normalized = normalize_entity_name("Mỹ Đình", entity_type="stadium")
print(f"'Mỹ Đình' normalized to: '{normalized}'")

# Try searching
results = kg.search_entities("Mỹ Đình", limit=3)
print(f"\nSearch 'Mỹ Đình' found: {[r.name for r in results]}")

results = kg.search_entities(normalized, limit=3)
print(f"Search '{normalized}' found: {[r.name for r in results]}")

# Get location
query = """
MATCH (s {name: 'Sân vận động Quốc gia Mỹ Đình'})-[r:LOCATED_IN]->(loc)
RETURN loc.name as location
"""
result = kg.driver.execute_query(query)
if result.records:
    print(f"\n✅ Correct answer: {result.records[0]['location']}")

kg.close()
