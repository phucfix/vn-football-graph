#!/usr/bin/env python3
"""
Phân tích các fields trong Infobox chưa được parse

Mục đích: Tìm xem còn thông tin gì trong Infobox có thể enrich thêm vào Knowledge Graph
"""

import json
import mwparserfromhell
from collections import Counter
from pathlib import Path

# Currently parsed fields
CURRENT_FIELDS = {
    'wiki_id', 'wiki_url', 'wiki_title', 'name', 'full_name', 
    'date_of_birth', 'place_of_birth', 'nationality', 'position', 
    'height', 'current_club', 'clubs_history', 'national_team_history'
}

def extract_infobox_fields(wikitext):
    """Extract all fields from infobox"""
    wikicode = mwparserfromhell.parse(wikitext)
    templates = wikicode.filter_templates()
    
    for template in templates:
        template_name = str(template.name).strip().lower()
        if 'infobox' in template_name or 'thông tin' in template_name:
            fields = {}
            for param in template.params:
                key = str(param.name).strip()
                value = str(param.value).strip()
                if value:  # Only include non-empty fields
                    fields[key] = value
            return fields
    return {}

def main():
    raw_dir = Path('data/raw')
    
    # Counters for all fields
    all_fields = Counter()
    sample_values = {}  # Store sample values for each field
    
    # Analyze player files
    print("📊 Analyzing Player Infoboxes...")
    print("=" * 80)
    
    player_files = list(raw_dir.glob('player_*.json'))[:100]  # Sample 100 players
    
    for file_path in player_files:
        with open(file_path) as f:
            data = json.load(f)
            
        wikitext = data.get('wikitext', '')
        fields = extract_infobox_fields(wikitext)
        
        for field_name, value in fields.items():
            all_fields[field_name] += 1
            if field_name not in sample_values:
                sample_values[field_name] = value[:100]  # Store first 100 chars
    
    print(f"\n📝 Found {len(all_fields)} unique fields in {len(player_files)} player infoboxes\n")
    
    # Categorize fields
    print("=" * 80)
    print("🔴 MISSING FIELDS (NOT CURRENTLY PARSED)")
    print("=" * 80)
    
    # Map Vietnamese to English field names
    field_mapping = {
        'name': 'name',
        'fullname': 'full_name',
        'birth_date': 'date_of_birth',
        'birth_place': 'place_of_birth',
        'height': 'height',
        'position': 'position',
        'currentclub': 'current_club',
        'years': 'clubs_history',
        'clubs': 'clubs_history',
        'nationalyears': 'national_team_history',
        'nationalteam': 'national_team_history',
    }
    
    missing_fields = []
    
    for field_name, count in all_fields.most_common():
        field_lower = field_name.lower().replace(' ', '').replace('_', '')
        
        # Check if this field is currently parsed
        is_parsed = False
        for mapped_field in field_mapping.keys():
            if mapped_field in field_lower or field_lower in mapped_field:
                is_parsed = True
                break
        
        if not is_parsed and count >= 5:  # Only show fields that appear in 5+ players
            missing_fields.append((field_name, count, sample_values[field_name]))
    
    # Group by category
    print("\n🏆 AWARDS & HONORS:")
    for field_name, count, sample in missing_fields:
        if any(kw in field_name.lower() for kw in ['award', 'honour', 'honor', 'giải thưởng', 'huy chương', 'vinh danh']):
            print(f"  {field_name:30s} | {count:3d} occurrences | Sample: {sample}")
    
    print("\n📊 STATISTICS:")
    for field_name, count, sample in missing_fields:
        if any(kw in field_name.lower() for kw in ['caps', 'goals', 'appearances', 'stats', 'thống kê', 'bàn thắng', 'trận', 'ghi bàn']):
            print(f"  {field_name:30s} | {count:3d} occurrences | Sample: {sample}")
    
    print("\n👔 CAREER INFO:")
    for field_name, count, sample in missing_fields:
        if any(kw in field_name.lower() for kw in ['manageryears', 'managerclubs', 'coach', 'huấn luyện', 'manage', 'quản lý']):
            print(f"  {field_name:30s} | {count:3d} occurrences | Sample: {sample}")
    
    print("\n🏢 CURRENT STATUS:")
    for field_name, count, sample in missing_fields:
        if any(kw in field_name.lower() for kw in ['clubnumber', 'số áo', 'number', 'pcupdate', 'ntupdate', 'cập nhật']):
            print(f"  {field_name:30s} | {count:3d} occurrences | Sample: {sample}")
    
    print("\n📚 OTHER INFO:")
    for field_name, count, sample in missing_fields:
        if not any(kw in field_name.lower() for kw in [
            'award', 'honour', 'honor', 'giải thưởng', 'huy chương', 'vinh danh',
            'caps', 'goals', 'appearances', 'stats', 'thống kê', 'bàn thắng', 'trận', 'ghi bàn',
            'manageryears', 'managerclubs', 'coach', 'huấn luyện', 'manage', 'quản lý',
            'clubnumber', 'số áo', 'number', 'pcupdate', 'ntupdate', 'cập nhật'
        ]):
            print(f"  {field_name:30s} | {count:3d} occurrences | Sample: {sample}")
    
    print("\n" + "=" * 80)
    print("📈 ENRICHMENT POTENTIAL")
    print("=" * 80)
    
    # Calculate potential new relationships
    goals_fields = sum(count for field, count, _ in missing_fields if 'goal' in field.lower() or 'bàn thắng' in field.lower())
    caps_fields = sum(count for field, count, _ in missing_fields if 'caps' in field.lower() or 'trận' in field.lower())
    awards_fields = sum(count for field, count, _ in missing_fields if 'award' in field.lower() or 'giải thưởng' in field.lower())
    
    print(f"\n✅ Có thể thêm:")
    print(f"  - Goals/Caps statistics: ~{goals_fields + caps_fields} relationships")
    print(f"  - Awards & Honors: ~{awards_fields} relationships")
    print(f"  - Career numbers: ~{sum(1 for f, c, _ in missing_fields if 'number' in f.lower())} relationships")
    
    print(f"\n💡 Khuyến nghị:")
    print(f"  1. Parse caps/goals cho club và national team history")
    print(f"  2. Parse awards/honors (Quả bóng vàng, vô địch, ...)")
    print(f"  3. Parse club number (số áo)")
    print(f"  4. Parse manager/coach career (nếu retired làm HLV)")

if __name__ == '__main__':
    main()
