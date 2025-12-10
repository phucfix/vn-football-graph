"""
STRICT NLP ENRICHMENT PIPELINE - VERSION 2.0

Cải tiến so với version cũ:
1. Strict entity matching - chỉ match entities đã có trong Neo4j
2. Confidence threshold cao hơn (>= 0.9)
3. Validation rules chặt chẽ
4. No fuzzy matching - exact match only
5. Context verification - kiểm tra context có hợp lý không

Mục tiêu: Đạt yêu cầu đồ án nhưng tránh false positives
"""

import os
import json
import logging
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from pathlib import Path

from neo4j import GraphDatabase
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class StrictNLPEnrichment:
    """
    Strict NLP Enrichment Pipeline.
    
    Đặc điểm:
    - Chỉ extract entities đã có trong Neo4j (no new entities)
    - Confidence threshold cao (>= 0.9)
    - Validation rules chặt chẽ
    - Không tạo quan hệ mơ hồ
    """
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        
        # Load existing entities từ Neo4j
        self.players = {}  # name -> wiki_id
        self.clubs = {}
        self.provinces = {}
        self.coaches = {}
        self.competitions = {}
        
        self._load_existing_entities()
    
    def _load_existing_entities(self):
        """Load tất cả entities hiện có trong Neo4j."""
        logger.info("Loading existing entities from Neo4j...")
        
        with self.driver.session() as session:
            # Players
            result = session.run("MATCH (p:Player) RETURN p.name as name, p.wiki_id as wiki_id")
            for r in result:
                if r['name']:
                    self.players[r['name'].lower()] = r['wiki_id']
            
            # Clubs
            result = session.run("MATCH (c:Club) RETURN c.name as name, c.wiki_id as wiki_id")
            for r in result:
                if r['name']:
                    self.clubs[r['name'].lower()] = r['wiki_id']
            
            # Provinces
            result = session.run("MATCH (p:Province) RETURN p.name as name")
            for r in result:
                if r['name']:
                    self.provinces[r['name'].lower()] = r['name']
            
            # Coaches
            result = session.run("MATCH (c:Coach) RETURN c.name as name, c.wiki_id as wiki_id")
            for r in result:
                if r['name']:
                    self.coaches[r['name'].lower()] = r['wiki_id']
            
            # Competitions
            result = session.run("MATCH (c:Competition) RETURN c.name as name, c.wiki_id as wiki_id")
            for r in result:
                if r['name']:
                    self.competitions[r['name'].lower()] = r['wiki_id']
        
        logger.info(f"Loaded: {len(self.players)} players, {len(self.clubs)} clubs, "
                   f"{len(self.provinces)} provinces, {len(self.coaches)} coaches, "
                   f"{len(self.competitions)} competitions")
    
    def strict_entity_recognition(self, text: str) -> List[Dict]:
        """
        NER với strict matching - chỉ nhận entities đã có trong Neo4j.
        
        Returns:
            List[Dict]: [{"text": "Nguyễn Quang Hải", "type": "PLAYER", "wiki_id": 123}]
        """
        text_lower = text.lower()
        entities = []
        
        # Common words to filter out (avoid false positives)
        stopwords = {'anh', 'chị', 'em', 'ông', 'bà', 'cô', 'bác', 'các', 'một', 'là', 'của'}
        
        # Match players (ưu tiên tên dài trước để tránh ambiguity)
        for player_name in sorted(self.players.keys(), key=len, reverse=True):
            if len(player_name) < 5:  # Skip very short names
                continue
            if player_name in text_lower:
                # Word boundary check
                import re
                pattern = r'\b' + re.escape(player_name) + r'\b'
                if re.search(pattern, text_lower):
                    entities.append({
                        "text": player_name,
                        "type": "PLAYER",
                        "wiki_id": self.players[player_name],
                        "confidence": 1.0  # Exact match
                    })
        
        # Match clubs
        for club_name in sorted(self.clubs.keys(), key=len, reverse=True):
            if len(club_name) < 5:  # Skip very short names
                continue
            if club_name in text_lower:
                import re
                pattern = r'\b' + re.escape(club_name) + r'\b'
                if re.search(pattern, text_lower):
                    entities.append({
                        "text": club_name,
                        "type": "CLUB",
                        "wiki_id": self.clubs[club_name],
                        "confidence": 1.0
                    })
        
        # Match provinces (skip common words)
        for prov_name in sorted(self.provinces.keys(), key=len, reverse=True):
            if prov_name in stopwords:  # Skip common words
                continue
            if len(prov_name) < 4:  # Skip very short names
                continue
            if prov_name in text_lower:
                import re
                pattern = r'\b' + re.escape(prov_name) + r'\b'
                if re.search(pattern, text_lower):
                    entities.append({
                        "text": prov_name,
                        "type": "PROVINCE",
                        "confidence": 1.0
                    })
        
        # Match coaches
        for coach_name in sorted(self.coaches.keys(), key=len, reverse=True):
            if coach_name in text_lower:
                entities.append({
                    "text": coach_name,
                    "type": "COACH",
                    "wiki_id": self.coaches[coach_name],
                    "confidence": 1.0
                })
        
        # Match competitions
        for comp_name in sorted(self.competitions.keys(), key=len, reverse=True):
            if comp_name in text_lower:
                entities.append({
                    "text": comp_name,
                    "type": "COMPETITION",
                    "wiki_id": self.competitions[comp_name],
                    "confidence": 1.0
                })
        
        # Deduplicate (keep longest match)
        seen_texts = set()
        unique_entities = []
        for ent in sorted(entities, key=lambda x: len(x['text']), reverse=True):
            if ent['text'] not in seen_texts:
                unique_entities.append(ent)
                seen_texts.add(ent['text'])
        
        return unique_entities
    
    def strict_relation_extraction(self, text: str, entities: List[Dict]) -> List[Dict]:
        """
        Relation extraction với strict rules.
        
        Chỉ extract khi:
        1. Có đủ 2 entities phù hợp
        2. Pattern rõ ràng (không mơ hồ)
        3. Context hợp lý
        """
        text_lower = text.lower()
        relations = []
        
        # Tạo entity lookup
        players = [e for e in entities if e['type'] == 'PLAYER']
        clubs = [e for e in entities if e['type'] == 'CLUB']
        provinces = [e for e in entities if e['type'] == 'PROVINCE']
        coaches = [e for e in entities if e['type'] == 'COACH']
        competitions = [e for e in entities if e['type'] == 'COMPETITION']
        
        # Pattern 1: PLAYED_FOR (player -> club)
        # Chỉ match khi có verb rõ ràng: "chơi cho", "thi đấu cho", "khoác áo"
        if players and clubs:
            play_verbs = ["chơi cho", "thi đấu cho", "khoác áo", "gia nhập", "chuyển đến"]
            for verb in play_verbs:
                if verb in text_lower:
                    for player in players:
                        for club in clubs:
                            # Kiểm tra thứ tự: player phải xuất hiện trước club
                            player_pos = text_lower.find(player['text'])
                            club_pos = text_lower.find(club['text'])
                            verb_pos = text_lower.find(verb)
                            
                            if player_pos < verb_pos < club_pos:
                                # Extract context window
                                context_start = max(0, player_pos - 50)
                                context_end = min(len(text), club_pos + 50)
                                context = text[context_start:context_end]
                                
                                relations.append({
                                    "subject": player,
                                    "predicate": "PLAYED_FOR",
                                    "object": club,
                                    "confidence": 0.95,
                                    "context": context,
                                    "pattern": verb
                                })
        
        # Pattern 2: BORN_IN (player -> province)
        if players and provinces:
            birth_verbs = ["sinh ra", "sinh tại", "quê ở", "quê quán"]
            for verb in birth_verbs:
                if verb in text_lower:
                    for player in players:
                        for province in provinces:
                            player_pos = text_lower.find(player['text'])
                            prov_pos = text_lower.find(province['text'])
                            verb_pos = text_lower.find(verb)
                            
                            if player_pos < verb_pos < prov_pos:
                                context_start = max(0, player_pos - 50)
                                context_end = min(len(text), prov_pos + 50)
                                context = text[context_start:context_end]
                                
                                relations.append({
                                    "subject": player,
                                    "predicate": "BORN_IN",
                                    "object": province,
                                    "confidence": 0.95,
                                    "context": context,
                                    "pattern": verb
                                })
        
        # Pattern 3: COACHED (coach -> club)
        if coaches and clubs:
            coach_verbs = ["huấn luyện", "dẫn dắt", "làm hlv"]
            for verb in coach_verbs:
                if verb in text_lower:
                    for coach in coaches:
                        for club in clubs:
                            coach_pos = text_lower.find(coach['text'])
                            club_pos = text_lower.find(club['text'])
                            verb_pos = text_lower.find(verb)
                            
                            if coach_pos < verb_pos < club_pos:
                                context_start = max(0, coach_pos - 50)
                                context_end = min(len(text), club_pos + 50)
                                context = text[context_start:context_end]
                                
                                relations.append({
                                    "subject": coach,
                                    "predicate": "COACHED",
                                    "object": club,
                                    "confidence": 0.95,
                                    "context": context,
                                    "pattern": verb
                                })
        
        # Pattern 4: COMPETED_IN (player/club -> competition)
        # CHỈ match khi có context rõ ràng về vô địch/tham gia
        if (players or clubs) and competitions:
            compete_phrases = ["vô địch", "tham dự", "tham gia", "giành"]
            for phrase in compete_phrases:
                if phrase in text_lower:
                    entities_to_match = players + clubs
                    for entity in entities_to_match:
                        for comp in competitions:
                            ent_pos = text_lower.find(entity['text'])
                            comp_pos = text_lower.find(comp['text'])
                            phrase_pos = text_lower.find(phrase)
                            
                            # Entity và competition phải gần phrase
                            if abs(ent_pos - phrase_pos) < 100 and abs(comp_pos - phrase_pos) < 100:
                                context_start = max(0, min(ent_pos, comp_pos) - 50)
                                context_end = min(len(text), max(ent_pos, comp_pos) + 50)
                                context = text[context_start:context_end]
                                
                                relations.append({
                                    "subject": entity,
                                    "predicate": "COMPETED_IN",
                                    "object": comp,
                                    "confidence": 0.90,
                                    "context": context,
                                    "pattern": phrase
                                })
        
        return relations
    
    def validate_relation(self, relation: Dict) -> bool:
        """
        Validate relation trước khi import.
        
        Rules:
        1. Confidence >= 0.9
        2. Context length >= 20 characters
        3. Subject và object phải khác nhau
        4. Không có từ phủ định gần pattern
        """
        # Rule 1: Confidence threshold
        if relation['confidence'] < 0.90:
            return False
        
        # Rule 2: Context length
        if len(relation.get('context', '')) < 20:
            return False
        
        # Rule 3: Subject != Object
        if relation['subject']['text'] == relation['object']['text']:
            return False
        
        # Rule 4: Không có từ phủ định
        context_lower = relation.get('context', '').lower()
        negative_words = ['không', 'chưa', 'chẳng', 'không phải', 'chưa từng']
        for neg in negative_words:
            if neg in context_lower:
                # Kiểm tra xem từ phủ định có gần pattern không
                pattern = relation.get('pattern', '')
                neg_pos = context_lower.find(neg)
                pattern_pos = context_lower.find(pattern)
                if abs(neg_pos - pattern_pos) < 20:
                    return False
        
        return True
    
    def import_to_neo4j(self, relations: List[Dict], source_file: str):
        """Import validated relations vào Neo4j."""
        logger.info(f"Importing {len(relations)} relations from {source_file}...")
        
        imported = 0
        skipped = 0
        
        with self.driver.session() as session:
            for rel in relations:
                if not self.validate_relation(rel):
                    skipped += 1
                    continue
                
                subj = rel['subject']
                obj = rel['object']
                pred = rel['predicate']
                
                # Create relationship
                try:
                    if pred == "PLAYED_FOR":
                        query = """
                        MATCH (p:Player {wiki_id: $subj_id})
                        MATCH (c:Club {wiki_id: $obj_id})
                        MERGE (p)-[r:PLAYED_FOR]->(c)
                        SET r.source = 'strict_nlp_v2',
                            r.confidence = $confidence,
                            r.context = $context,
                            r.pattern = $pattern,
                            r.imported_at = datetime()
                        """
                    elif pred == "BORN_IN":
                        query = """
                        MATCH (p:Player {wiki_id: $subj_id})
                        MATCH (pr:Province {name: $obj_name})
                        MERGE (p)-[r:BORN_IN]->(pr)
                        SET r.source = 'strict_nlp_v2',
                            r.confidence = $confidence,
                            r.context = $context,
                            r.pattern = $pattern,
                            r.imported_at = datetime()
                        """
                    elif pred == "COACHED":
                        query = """
                        MATCH (co:Coach {wiki_id: $subj_id})
                        MATCH (c:Club {wiki_id: $obj_id})
                        MERGE (co)-[r:COACHED]->(c)
                        SET r.source = 'strict_nlp_v2',
                            r.confidence = $confidence,
                            r.context = $context,
                            r.pattern = $pattern,
                            r.imported_at = datetime()
                        """
                    elif pred == "COMPETED_IN":
                        # Determine subject type
                        if subj['type'] == 'PLAYER':
                            query = """
                            MATCH (p:Player {wiki_id: $subj_id})
                            MATCH (comp:Competition {wiki_id: $obj_id})
                            MERGE (p)-[r:COMPETED_IN]->(comp)
                            SET r.source = 'strict_nlp_v2',
                                r.confidence = $confidence,
                                r.context = $context,
                                r.pattern = $pattern,
                                r.imported_at = datetime()
                            """
                        else:  # CLUB
                            query = """
                            MATCH (c:Club {wiki_id: $subj_id})
                            MATCH (comp:Competition {wiki_id: $obj_id})
                            MERGE (c)-[r:COMPETED_IN]->(comp)
                            SET r.source = 'strict_nlp_v2',
                                r.confidence = $confidence,
                                r.context = $context,
                                r.pattern = $pattern,
                                r.imported_at = datetime()
                            """
                    else:
                        continue
                    
                    session.run(query,
                               subj_id=subj.get('wiki_id'),
                               obj_id=obj.get('wiki_id'),
                               obj_name=obj.get('text'),
                               confidence=rel['confidence'],
                               context=rel['context'],
                               pattern=rel['pattern'])
                    
                    imported += 1
                    
                except Exception as e:
                    logger.error(f"Error importing relation: {e}")
                    skipped += 1
        
        logger.info(f"Imported: {imported}, Skipped: {skipped}")
        return imported, skipped
    
    def close(self):
        self.driver.close()


def main():
    """
    Main enrichment pipeline.
    
    Steps:
    1. Load text sources
    2. Extract entities (strict matching với Neo4j)
    3. Extract relations (strict patterns)
    4. Validate relations
    5. Import to Neo4j với source='strict_nlp_v2'
    """
    print("=" * 80)
    print("🔬 STRICT NLP ENRICHMENT PIPELINE V2.0")
    print("=" * 80)
    print()
    
    enricher = StrictNLPEnrichment()
    
    try:
        # Load text sources (sử dụng processed_texts hoặc Wikipedia text)
        text_dir = Path("data/processed_texts")
        if not text_dir.exists():
            text_dir = Path("data/text_sources")
        
        if not text_dir.exists():
            print("❌ No text sources found!")
            print("   Please run text collection first.")
            return
        
        text_files = list(text_dir.glob("*.txt"))
        print(f"📁 Found {len(text_files)} text files")
        print()
        
        # Process each file
        total_relations = []
        
        for i, fpath in enumerate(text_files[:100], 1):  # Process first 100 files
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Extract entities
                entities = enricher.strict_entity_recognition(text)
                
                if len(entities) < 2:
                    continue  # Skip if too few entities
                
                # Extract relations
                relations = enricher.strict_relation_extraction(text, entities)
                
                if relations:
                    total_relations.extend(relations)
                    print(f"[{i}/{len(text_files)}] {fpath.name}: {len(entities)} entities, {len(relations)} relations")
            
            except Exception as e:
                logger.error(f"Error processing {fpath}: {e}")
        
        print()
        print(f"📊 Total relations extracted: {len(total_relations)}")
        print()
        
        # Import to Neo4j
        print("💾 Importing to Neo4j...")
        imported, skipped = enricher.import_to_neo4j(total_relations, "text_sources")
        
        print()
        print("=" * 80)
        print("✅ ENRICHMENT COMPLETED")
        print("=" * 80)
        print(f"   Extracted: {len(total_relations)}")
        print(f"   Imported: {imported}")
        print(f"   Skipped: {skipped}")
        print(f"   Success rate: {imported/len(total_relations)*100:.1f}%")
        
    finally:
        enricher.close()


if __name__ == "__main__":
    main()
