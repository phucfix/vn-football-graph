#!/usr/bin/env python3
"""
Kiểm tra tên các club trong database
"""

from chatbot.knowledge_graph import KnowledgeGraph
import logging

logging.basicConfig(level=logging.INFO)

def check_clubs():
    kg = KnowledgeGraph()
    kg.connect()
    
    # Get all clubs
    clubs = kg.execute_cypher("MATCH (c:Club) RETURN c.name ORDER BY c.name")
    
    print("📋 CÁC CLB TRONG DATABASE:")
    print("=" * 50)
    
    for i, record in enumerate(clubs, 1):
        club_name = record['c.name']
        print(f"{i:2d}. {club_name}")
    
    print(f"\n📊 Tổng cộng: {len(clubs)} club")

def check_player_clubs():
    kg = KnowledgeGraph()
    kg.connect()
    
    # Check specific players
    test_players = ["Nguyễn Quang Hải", "Nguyễn Công Phượng", "Đoàn Văn Hậu"]
    
    for player in test_players:
        clubs = kg.execute_cypher(
            "MATCH (p:Player {name: $player})-[:PLAYED_FOR]->(c:Club) RETURN c.name",
            {"player": player}
        )
        
        print(f"\n🔍 {player}:")
        if clubs:
            for record in clubs:
                print(f"   ⚽ {record['c.name']}")
        else:
            print("   ❌ Không tìm thấy")

def check_provinces():
    kg = KnowledgeGraph()
    kg.connect()
    
    # Get all provinces
    provinces = kg.execute_cypher("MATCH (p:Province) RETURN p.name ORDER BY p.name")
    
    print("\n📍 CÁC TỈNH/THÀNH PHỐ:")
    print("=" * 50)
    
    for record in provinces:
        print(f"   📍 {record['p.name']}")

if __name__ == "__main__":
    check_clubs()
    check_player_clubs()
    check_provinces()
