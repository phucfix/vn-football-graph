#!/usr/bin/env python3
"""
Debug Công Phượng
"""

from chatbot.knowledge_graph import KnowledgeGraph
import logging

logging.basicConfig(level=logging.INFO)

def debug_cong_phuong():
    kg = KnowledgeGraph()
    kg.connect()
    
    # Check Công Phượng clubs
    clubs = kg.execute_cypher(
        "MATCH (p:Player {name: 'Nguyễn Công Phượng'})-[:PLAYED_FOR]->(c:Club) RETURN c.name ORDER BY c.name"
    )
    
    print("🔍 CÔNG PHƯỢNG - CÁC CLB:")
    for record in clubs:
        club_name = record['c.name']
        print(f"   ⚽ {club_name}")
        if 'hagl' in club_name.lower() or 'hoàng anh gia lai' in club_name.lower():
            print(f"      --> HAGL MATCH!")
    
    # Check if HAGL alias mapping works
    from chatbot.llm_chatbot import LLMGraphChatbot
    chatbot = LLMGraphChatbot()
    chatbot.initialize()
    
    # Test club finding
    club_found = chatbot.graph_chatbot._find_club("HAGL")
    print(f"\n🔍 _find_club('HAGL') = {club_found}")
    
    # Test player-club check
    if club_found:
        result = chatbot.graph_chatbot.check_player_club("Nguyễn Công Phượng", club_found)
        print(f"✅ check_player_club('Nguyễn Công Phượng', '{club_found}') = {result}")

if __name__ == "__main__":
    debug_cong_phuong()
