"""
Manual fix: Add PLAYED_FOR relationships for major players
Based on real career data from Wikipedia
"""
from chatbot.knowledge_graph import get_kg

def add_played_for_relationship(kg, player_name: str, club_name: str, year_start: int = None, year_end: int = None):
    """Add PLAYED_FOR relationship between player and club"""
    
    # Check if both exist
    check_query = """
    MATCH (p:Player {name: $player_name})
    OPTIONAL MATCH (c:Club {name: $club_name})
    RETURN p.name as player, c.name as club
    """
    result = kg.driver.execute_query(check_query, player_name=player_name, club_name=club_name)
    
    if not result.records or not result.records[0]['player']:
        print(f"   ❌ Player '{player_name}' not found")
        return False
    if not result.records[0]['club']:
        print(f"   ❌ Club '{club_name}' not found")
        return False
    
    # Create relationship
    create_query = """
    MATCH (p:Player {name: $player_name})
    MATCH (c:Club {name: $club_name})
    MERGE (p)-[r:PLAYED_FOR]->(c)
    """
    if year_start:
        create_query += f" ON CREATE SET r.year_start = {year_start}"
    if year_end:
        create_query += f" ON CREATE SET r.year_end = {year_end}"
    
    kg.driver.execute_query(create_query, player_name=player_name, club_name=club_name)
    print(f"   ✅ {player_name} -[PLAYED_FOR]-> {club_name}")
    return True

def main():
    kg = get_kg()
    
    print("=" * 70)
    print("MANUAL FIX: ADDING PLAYED_FOR RELATIONSHIPS")
    print("=" * 70)
    
    # Data based on Wikipedia career information
    player_clubs = [
        # Nguyễn Công Phượng
        ("Nguyễn Công Phượng", "Học viện Bóng đáHoàng Anh Gia Lai", 2011, 2017),
        ("Nguyễn Công Phượng", "Câu lạc bộ bóng đá Hoàng Anh Gia Lai", 2015, 2021),
        
        # Nguyễn Quang Hải  
        ("Nguyễn Quang Hải", "Câu lạc bộ bóng đá Hà Nội", 2016, 2023),
        
        # Nguyễn Văn Toàn
        ("Nguyễn Văn Toàn", "Học viện Bóng đáHoàng Anh Gia Lai", 2013, None),
        ("Nguyễn Văn Toàn", "Câu lạc bộ bóng đá Hoàng Anh Gia Lai", 2015, None),
        
        # Đoàn Văn Hậu
        ("Đoàn Văn Hậu", "Câu lạc bộ bóng đá Hà Nội", 2017, None),
        
        # Lương Xuân Trường
        ("Lương Xuân Trường", "Học viện Bóng đáHoàng Anh Gia Lai", 2011, 2016),
        ("Lương Xuân Trường", "Câu lạc bộ bóng đá Hoàng Anh Gia Lai", 2016, None),
        
        # Nguyễn Tiến Linh
        ("Nguyễn Tiến Linh", "Câu lạc bộ bóng đá Hà Nội", 2015, 2020),
        ("Nguyễn Tiến Linh", "Câu lạc bộ bóng đá Bình Dương", 2020, None),
        
        # Hà Đức Chinh
        ("Hà Đức Chinh", "Câu lạc bộ bóng đá SHB Đà Nẵng", 2016, None),
        
        # Đỗ Hùng Dũng
        ("Đỗ Hùng Dũng", "Câu lạc bộ bóng đá Hà Nội", 2013, None),
        
        # Nguyễn Văn Quyết
        ("Nguyễn Văn Quyết", "Câu lạc bộ bóng đá Hà Nội", 2009, None),
    ]
    
    success = 0
    failed = 0
    
    for player, club, year_start, year_end in player_clubs:
        print(f"\n🔧 Adding: {player} -> {club} ({year_start or '?'}-{year_end or 'present'})")
        if add_played_for_relationship(kg, player, club, year_start, year_end):
            success += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"✅ Success: {success}")
    print(f"❌ Failed: {failed}")
    print("=" * 70)
    
    # Verify Công Phượng
    print("\n🔍 Verifying Công Phượng...")
    query = """
    MATCH (p:Player {name: 'Nguyễn Công Phượng'})-[r:PLAYED_FOR]->(c)
    RETURN c.name as club, r.year_start as start, r.year_end as end
    """
    result = kg.driver.execute_query(query)
    
    if result.records:
        print(f"   ✅ Found {len(result.records)} clubs:")
        for record in result.records:
            print(f"      - {record['club']} ({record['start']}-{record['end'] or 'present'})")
    else:
        print("   ❌ Still no PLAYED_FOR relationships!")
    
    kg.close()

if __name__ == "__main__":
    main()
