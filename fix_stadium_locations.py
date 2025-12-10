"""
Manual fix: Verify and ensure all stadiums have correct LOCATED_IN relationships
"""
from chatbot.knowledge_graph import get_kg

def main():
    kg = get_kg()
    
    print("=" * 70)
    print("CHECKING ALL STADIUMS LOCATED_IN")
    print("=" * 70)
    
    # Get all stadiums
    query = """
    MATCH (s:Stadium)
    RETURN s.name as name, s.province as province
    ORDER BY name
    LIMIT 20
    """
    
    result = kg.driver.execute_query(query)
    
    print(f"\n📋 Found {len(result.records)} stadiums:")
    
    for record in result.records:
        name = record['name']
        province_prop = record['province']
        
        # Check LOCATED_IN relationship
        check_query = """
        MATCH (s:Stadium {name: $name})-[r:LOCATED_IN]->(p)
        RETURN p.name as location
        """
        check_result = kg.driver.execute_query(check_query, name=name)
        
        if check_result.records:
            location = check_result.records[0]['location']
            print(f"   ✅ {name[:50]} -> {location}")
        else:
            print(f"   ❌ {name[:50]} -> NO RELATIONSHIP (property: {province_prop})")
            
            # Try to fix if province property exists
            if province_prop:
                # Check if province exists
                province_query = """
                MATCH (p:Province {name: $province})
                RETURN p.name as name
                """
                prov_result = kg.driver.execute_query(province_query, province=province_prop)
                
                if prov_result.records:
                    # Create relationship
                    fix_query = """
                    MATCH (s:Stadium {name: $stadium})
                    MATCH (p:Province {name: $province})
                    MERGE (s)-[r:LOCATED_IN]->(p)
                    RETURN 'created' as status
                    """
                    kg.driver.execute_query(fix_query, stadium=name, province=province_prop)
                    print(f"      🔧 FIXED: Created LOCATED_IN -> {province_prop}")
                else:
                    print(f"      ⚠️  Province '{province_prop}' not found in database")
    
    # Verify Mỹ Đình specifically
    print("\n" + "=" * 70)
    print("VERIFY: SÂN MỸ ĐÌNH")
    print("=" * 70)
    
    query = """
    MATCH (s:Stadium {name: 'Sân vận động Quốc gia Mỹ Đình'})-[r:LOCATED_IN]->(p)
    RETURN p.name as location, labels(p) as labels
    """
    
    result = kg.driver.execute_query(query)
    
    if result.records:
        for record in result.records:
            print(f"✅ Sân Mỹ Đình -[LOCATED_IN]-> {record['location']} {record['labels']}")
    else:
        print("❌ Still no LOCATED_IN relationship!")
    
    kg.close()

if __name__ == "__main__":
    main()
