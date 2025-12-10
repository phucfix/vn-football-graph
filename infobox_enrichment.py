#!/usr/bin/env python3
"""
Infobox Re-Parser and Enrichment

Re-parse Wikipedia infoboxes to extract missing information:
- Clubs history with caps/goals
- National team history with caps/goals  
- Current club
- Club number

This will FIX players with 0 relationships and ENRICH existing players.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import mwparserfromhell
from dotenv import load_dotenv
from neo4j import GraphDatabase
from tqdm import tqdm
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class InfoboxEnrichmentParser:
    """Enhanced parser to extract caps/goals and other missing data"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def close(self):
        self.driver.close()
    
    def parse_year_range(self, year_str: str) -> tuple:
        """Parse year range like '2012-15' or '2012-2015' or '2012-present'"""
        year_str = str(year_str).strip()
        
        # Handle 'present', 'hiện tại'
        if 'present' in year_str.lower() or 'hiện tại' in year_str.lower():
            match = re.search(r'(\d{4})', year_str)
            if match:
                return (int(match.group(1)), None)
        
        # Handle range like '2012-15' or '2012–2015'
        match = re.match(r'(\d{4})\s*[-–]\s*(\d{2,4})', year_str)
        if match:
            from_year = int(match.group(1))
            to_year_str = match.group(2)
            
            # If 2-digit year, add century
            if len(to_year_str) == 2:
                century = (from_year // 100) * 100
                to_year = century + int(to_year_str)
            else:
                to_year = int(to_year_str)
            
            return (from_year, to_year)
        
        # Single year
        match = re.search(r'(\d{4})', year_str)
        if match:
            year = int(match.group(1))
            return (year, year)
        
        return (None, None)
    
    def extract_clubs_history(self, infobox: Dict[str, str]) -> List[Dict]:
        """Extract clubs history with caps/goals"""
        clubs_history = []
        
        # Check for yearsN, clubsN, capsN, goalsN patterns
        i = 1
        while True:
            years_key = f'years{i}'
            clubs_key = f'clubs{i}'
            
            if years_key not in infobox or clubs_key not in infobox:
                break
            
            years_val = infobox[years_key]
            clubs_val = infobox[clubs_key]
            
            # Parse years
            from_year, to_year = self.parse_year_range(years_val)
            
            # Clean club name
            club_name = self._clean_entity_name(clubs_val)
            
            if club_name:
                entry = {
                    'club_name': club_name,
                    'from_year': from_year,
                    'to_year': to_year
                }
                
                # Add caps if available
                caps_key = f'caps{i}'
                if caps_key in infobox:
                    try:
                        caps = int(infobox[caps_key].strip())
                        entry['caps'] = caps
                    except:
                        pass
                
                # Add goals if available
                goals_key = f'goals{i}'
                if goals_key in infobox:
                    try:
                        goals = int(infobox[goals_key].strip())
                        entry['goals'] = goals
                    except:
                        pass
                
                clubs_history.append(entry)
            
            i += 1
        
        return clubs_history
    
    def extract_national_team_history(self, infobox: Dict[str, str]) -> List[Dict]:
        """Extract national team history with caps/goals"""
        nt_history = []
        
        i = 1
        while True:
            years_key = f'nationalyears{i}'
            team_key = f'nationalteam{i}'
            
            if years_key not in infobox or team_key not in infobox:
                break
            
            years_val = infobox[years_key]
            team_val = infobox[team_key]
            
            from_year, to_year = self.parse_year_range(years_val)
            team_name = self._clean_entity_name(team_val)
            
            if team_name:
                entry = {
                    'team_name': team_name,
                    'from_year': from_year,
                    'to_year': to_year
                }
                
                # Add caps
                caps_key = f'nationalcaps{i}'
                if caps_key in infobox:
                    try:
                        caps = int(infobox[caps_key].strip())
                        entry['caps'] = caps
                    except:
                        pass
                
                # Add goals
                goals_key = f'nationalgoals{i}'
                if goals_key in infobox:
                    try:
                        goals = int(infobox[goals_key].strip())
                        entry['goals'] = goals
                    except:
                        pass
                
                nt_history.append(entry)
            
            i += 1
        
        return nt_history
    
    def _clean_entity_name(self, text: str) -> str:
        """Clean entity name from wikitext"""
        # Remove wiki links: [[Link|Text]] → Text or [[Link]] → Link
        text = re.sub(r'\[\[([^\|\]]+)\|([^\]]+)\]\]', r'\2', text)
        text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
        
        # Remove refs, templates, etc
        text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
        text = re.sub(r'{{[^}]+}}', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def parse_player_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a single player file"""
        try:
            with open(file_path) as f:
                data = json.load(f)
            
            wikitext = data.get('wikitext', '')
            if not wikitext:
                return None
            
            # Parse infobox
            wikicode = mwparserfromhell.parse(wikitext)
            templates = wikicode.filter_templates()
            
            infobox_data = {}
            for template in templates:
                template_name = str(template.name).strip().lower()
                if 'infobox' in template_name or 'thông tin' in template_name:
                    for param in template.params:
                        key = str(param.name).strip().lower()
                        value = str(param.value).strip()
                        if value:
                            infobox_data[key] = value
                    break
            
            if not infobox_data:
                return None
            
            # Extract structured data
            result = {
                'wiki_id': data['page_id'],
                'wiki_title': data['page_title'],
                'name': infobox_data.get('name', data['page_title']),
                'clubs_history': self.extract_clubs_history(infobox_data),
                'national_team_history': self.extract_national_team_history(infobox_data)
            }
            
            # Extract current club
            if 'currentclub' in infobox_data:
                result['current_club'] = self._clean_entity_name(infobox_data['currentclub'])
            
            # Extract club number
            if 'clubnumber' in infobox_data:
                try:
                    result['club_number'] = int(infobox_data['clubnumber'].strip())
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None
    
    def import_to_neo4j(self, enriched_data: List[Dict]):
        """Import enriched data to Neo4j"""
        with self.driver.session() as session:
            stats = {
                'players_processed': 0,
                'clubs_added': 0,
                'national_teams_added': 0,
                'relationships_created': 0,
                'relationships_updated': 0
            }
            
            for player_data in tqdm(enriched_data, desc="Importing to Neo4j"):
                try:
                    # Match player
                    result = session.run('''
                        MATCH (p:Player {wiki_id: $wiki_id})
                        RETURN p
                    ''', wiki_id=player_data['wiki_id'])
                    
                    if not result.single():
                        logger.warning(f"Player not found: {player_data['name']} (wiki_id: {player_data['wiki_id']})")
                        continue
                    
                    stats['players_processed'] += 1
                    
                    # Import clubs history
                    for club in player_data.get('clubs_history', []):
                        session.run('''
                            MATCH (p:Player {wiki_id: $wiki_id})
                            MERGE (c:Club {name: $club_name})
                            MERGE (p)-[r:PLAYED_FOR]->(c)
                            SET r.from_year = $from_year,
                                r.to_year = $to_year,
                                r.caps = $caps,
                                r.goals = $goals,
                                r.source = 'infobox_enrichment',
                                r.updated_at = datetime()
                        ''', 
                            wiki_id=player_data['wiki_id'],
                            club_name=club['club_name'],
                            from_year=club.get('from_year'),
                            to_year=club.get('to_year'),
                            caps=club.get('caps'),
                            goals=club.get('goals')
                        )
                        stats['clubs_added'] += 1
                    
                    # Import national team history
                    for nt in player_data.get('national_team_history', []):
                        session.run('''
                            MATCH (p:Player {wiki_id: $wiki_id})
                            MERGE (nt:NationalTeam {name: $team_name})
                            MERGE (p)-[r:PLAYED_FOR_NATIONAL]->(nt)
                            SET r.from_year = $from_year,
                                r.to_year = $to_year,
                                r.caps = $caps,
                                r.goals = $goals,
                                r.source = 'infobox_enrichment',
                                r.updated_at = datetime()
                        ''',
                            wiki_id=player_data['wiki_id'],
                            team_name=nt['team_name'],
                            from_year=nt.get('from_year'),
                            to_year=nt.get('to_year'),
                            caps=nt.get('caps'),
                            goals=nt.get('goals')
                        )
                        stats['national_teams_added'] += 1
                
                except Exception as e:
                    logger.error(f"Error importing {player_data['name']}: {e}")
            
            return stats

def main():
    print("=" * 80)
    print("🔄 INFOBOX RE-PARSER AND ENRICHMENT")
    print("=" * 80)
    print()
    
    parser = InfoboxEnrichmentParser()
    
    try:
        # Find all player files
        raw_dir = Path('data/raw')
        player_files = list(raw_dir.glob('player_*.json'))
        
        print(f"📁 Found {len(player_files)} player files")
        print()
        
        # Parse all files
        print("📊 Parsing infoboxes...")
        enriched_data = []
        
        for file_path in tqdm(player_files, desc="Parsing"):
            data = parser.parse_player_file(file_path)
            if data and (data.get('clubs_history') or data.get('national_team_history')):
                enriched_data.append(data)
        
        print(f"\n✅ Parsed {len(enriched_data)} players with clubs/national team data")
        
        # Show sample
        if enriched_data:
            sample = enriched_data[0]
            print(f"\n📋 Sample: {sample['name']}")
            if sample.get('clubs_history'):
                print(f"  Clubs: {len(sample['clubs_history'])}")
                for club in sample['clubs_history'][:3]:
                    caps = club.get('caps', '?')
                    goals = club.get('goals', '?')
                    print(f"    - {club['club_name']:30s} ({club.get('from_year', '?')}-{club.get('to_year', '?')}) | {caps} caps, {goals} goals")
        
        # Ask confirmation
        print()
        confirm = input("❓ Import to Neo4j? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Cancelled")
            return
        
        # Import
        print("\n🚀 Importing to Neo4j...")
        stats = parser.import_to_neo4j(enriched_data)
        
        print("\n" + "=" * 80)
        print("✅ ENRICHMENT COMPLETED!")
        print("=" * 80)
        print(f"  Players processed: {stats['players_processed']}")
        print(f"  Club relationships: {stats['clubs_added']}")
        print(f"  National team relationships: {stats['national_teams_added']}")
        print(f"  Total relationships: {stats['clubs_added'] + stats['national_teams_added']}")
        
    finally:
        parser.close()

if __name__ == '__main__':
    main()
