"""
Bộ sinh câu hỏi đánh giá đơn giản

Chỉ tạo 2 loại câu hỏi:
1. Đúng/Sai - dựa trên mệnh đề về quan hệ trong KG
2. Trắc nghiệm - hỏi về thuộc tính của entity

Câu hỏi được tạo trực tiếp từ dữ liệu trong Neo4j, đảm bảo 100% chính xác.
"""

import json
import random
import logging
from typing import List, Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_questions(total: int = 2200) -> List[Dict]:
    """Sinh tập câu hỏi đánh giá từ Knowledge Graph."""
    
    from chatbot.knowledge_graph import KnowledgeGraph
    kg = KnowledgeGraph()
    kg.connect()
    
    def query(cypher: str) -> List[Dict]:
        return kg.execute_cypher(cypher)
    
    questions = []
    
    # Tính số lượng mỗi loại
    n_1hop = int(total * 0.4)  # 40% 1-hop yes/no
    n_2hop = int(total * 0.3)  # 30% 2-hop yes/no  
    n_mcq = total - n_1hop - n_2hop  # 30% MCQ
    
    per_type_1hop = n_1hop // 6  # 6 loại: 3 quan hệ x (đúng + sai)
    per_type_2hop = n_2hop // 4  # 4 loại: 2 quan hệ x (đúng + sai)
    per_type_mcq = n_mcq // 3  # 3 loại MCQ
    
    logger.info(f"Generating: {n_1hop} 1-hop, {n_2hop} 2-hop, {n_mcq} MCQ")
    
    # ==================== 1-HOP ĐÚNG/SAI ====================
    
    # Player -> Club (ĐÚNG)
    logger.info("Player-Club TRUE...")
    result = query(f"MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) RETURN p.name as player, c.name as club ORDER BY rand() LIMIT {per_type_1hop*2}")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'PLAYED_FOR' and q.get('answer') == 'ĐÚNG']) >= per_type_1hop:
            break
        if not r['player'] or not r['club'] or (r['player'], r['club']) in seen:
            continue
        seen.add((r['player'], r['club']))
        questions.append({
            "type": "yes_no", "question": f"{r['player']} đã chơi cho {r['club']}.",
            "answer": "ĐÚNG", "hops": 1, "relation": "PLAYED_FOR"
        })
    
    # Player -> Club (SAI)
    logger.info("Player-Club FALSE...")
    result = query(f"MATCH (p:Player), (c:Club) WHERE NOT (p)-[:PLAYED_FOR]->(c) WITH p, c, rand() as r ORDER BY r LIMIT {per_type_1hop*3} RETURN p.name as player, c.name as club")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'PLAYED_FOR' and q.get('answer') == 'SAI']) >= per_type_1hop:
            break
        if not r['player'] or not r['club'] or (r['player'], r['club']) in seen:
            continue
        seen.add((r['player'], r['club']))
        questions.append({
            "type": "yes_no", "question": f"{r['player']} đã chơi cho {r['club']}.",
            "answer": "SAI", "hops": 1, "relation": "PLAYED_FOR"
        })
    
    # Player -> Province (ĐÚNG)
    logger.info("Player-Province TRUE...")
    result = query(f"MATCH (p:Player)-[:BORN_IN]->(pr:Province) RETURN p.name as player, pr.name as province ORDER BY rand() LIMIT {per_type_1hop*2}")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'BORN_IN' and q.get('answer') == 'ĐÚNG']) >= per_type_1hop:
            break
        if not r['player'] or not r['province'] or r['player'] in seen:
            continue
        seen.add(r['player'])
        questions.append({
            "type": "yes_no", "question": f"{r['player']} sinh ra ở {r['province']}.",
            "answer": "ĐÚNG", "hops": 1, "relation": "BORN_IN"
        })
    
    # Player -> Province (SAI)
    logger.info("Player-Province FALSE...")
    result = query(f"MATCH (p:Player)-[:BORN_IN]->(pr1:Province), (pr2:Province) WHERE pr1 <> pr2 WITH p, pr2, rand() as r ORDER BY r LIMIT {per_type_1hop*3} RETURN p.name as player, pr2.name as province")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'BORN_IN' and q.get('answer') == 'SAI']) >= per_type_1hop:
            break
        if not r['player'] or not r['province'] or r['player'] in seen:
            continue
        seen.add(r['player'])
        questions.append({
            "type": "yes_no", "question": f"{r['player']} sinh ra ở {r['province']}.",
            "answer": "SAI", "hops": 1, "relation": "BORN_IN"
        })
    
    # Coach -> Club (ĐÚNG)
    logger.info("Coach-Club TRUE...")
    result = query(f"MATCH (co:Coach)-[:COACHED]->(c:Club) RETURN co.name as coach, c.name as club ORDER BY rand() LIMIT {per_type_1hop*2}")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'COACHED' and q.get('answer') == 'ĐÚNG']) >= per_type_1hop:
            break
        if not r['coach'] or not r['club'] or (r['coach'], r['club']) in seen:
            continue
        seen.add((r['coach'], r['club']))
        questions.append({
            "type": "yes_no", "question": f"{r['coach']} đã huấn luyện {r['club']}.",
            "answer": "ĐÚNG", "hops": 1, "relation": "COACHED"
        })
    
    # Coach -> Club (SAI)
    logger.info("Coach-Club FALSE...")
    result = query(f"MATCH (co:Coach), (c:Club) WHERE NOT (co)-[:COACHED]->(c) WITH co, c, rand() as r ORDER BY r LIMIT {per_type_1hop*3} RETURN co.name as coach, c.name as club")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'COACHED' and q.get('answer') == 'SAI']) >= per_type_1hop:
            break
        if not r['coach'] or not r['club'] or (r['coach'], r['club']) in seen:
            continue
        seen.add((r['coach'], r['club']))
        questions.append({
            "type": "yes_no", "question": f"{r['coach']} đã huấn luyện {r['club']}.",
            "answer": "SAI", "hops": 1, "relation": "COACHED"
        })
    
    # ==================== 2-HOP ĐÚNG/SAI ====================
    
    # Same Club (ĐÚNG)
    logger.info("Same Club TRUE (2-hop)...")
    result = query(f"MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player) WHERE p1.name < p2.name WITH p1, p2, rand() as r ORDER BY r LIMIT {per_type_2hop*2} RETURN p1.name as p1, p2.name as p2")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'SAME_CLUB' and q.get('answer') == 'ĐÚNG']) >= per_type_2hop:
            break
        if not r['p1'] or not r['p2'] or (r['p1'], r['p2']) in seen:
            continue
        seen.add((r['p1'], r['p2']))
        questions.append({
            "type": "yes_no", "question": f"{r['p1']} và {r['p2']} cùng chơi cho một câu lạc bộ.",
            "answer": "ĐÚNG", "hops": 2, "relation": "SAME_CLUB"
        })
    
    # Same Club (SAI) - Đơn giản hóa query
    logger.info("Same Club FALSE (2-hop)...")
    # Lấy tất cả cầu thủ có CLB
    all_players_with_clubs = query("MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) RETURN DISTINCT p.name as player, collect(c.name) as clubs")
    player_clubs = {r['player']: set(r['clubs']) for r in all_players_with_clubs if r['player']}
    players_list = list(player_clubs.keys())
    
    same_club_false_count = 0
    seen = set()
    random.shuffle(players_list)
    for i, p1 in enumerate(players_list):
        if same_club_false_count >= per_type_2hop:
            break
        for p2 in players_list[i+1:]:
            if same_club_false_count >= per_type_2hop:
                break
            # Kiểm tra không có CLB chung
            if not player_clubs[p1].intersection(player_clubs[p2]):
                key = tuple(sorted([p1, p2]))
                if key not in seen:
                    seen.add(key)
                    questions.append({
                        "type": "yes_no", "question": f"{p1} và {p2} cùng chơi cho một câu lạc bộ.",
                        "answer": "SAI", "hops": 2, "relation": "SAME_CLUB"
                    })
                    same_club_false_count += 1
    
    # Same Province (ĐÚNG)
    logger.info("Same Province TRUE (2-hop)...")
    result = query(f"MATCH (p1:Player)-[:BORN_IN]->(pr:Province)<-[:BORN_IN]-(p2:Player) WHERE p1.name < p2.name WITH p1, p2, rand() as r ORDER BY r LIMIT {per_type_2hop*2} RETURN p1.name as p1, p2.name as p2")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('relation') == 'SAME_PROVINCE' and q.get('answer') == 'ĐÚNG']) >= per_type_2hop:
            break
        if not r['p1'] or not r['p2'] or (r['p1'], r['p2']) in seen:
            continue
        seen.add((r['p1'], r['p2']))
        questions.append({
            "type": "yes_no", "question": f"{r['p1']} và {r['p2']} cùng quê.",
            "answer": "ĐÚNG", "hops": 2, "relation": "SAME_PROVINCE"
        })
    
    # Same Province (SAI) - Đơn giản hóa
    logger.info("Same Province FALSE (2-hop)...")
    all_players_with_provinces = query("MATCH (p:Player)-[:BORN_IN]->(pr:Province) RETURN p.name as player, pr.name as province")
    player_provinces = {r['player']: r['province'] for r in all_players_with_provinces if r['player'] and r['province']}
    players_with_prov = list(player_provinces.keys())
    
    same_prov_false_count = 0
    seen = set()
    random.shuffle(players_with_prov)
    for i, p1 in enumerate(players_with_prov):
        if same_prov_false_count >= per_type_2hop:
            break
        for p2 in players_with_prov[i+1:]:
            if same_prov_false_count >= per_type_2hop:
                break
            # Kiểm tra khác quê
            if player_provinces[p1] != player_provinces[p2]:
                key = tuple(sorted([p1, p2]))
                if key not in seen:
                    seen.add(key)
                    questions.append({
                        "type": "yes_no", "question": f"{p1} và {p2} cùng quê.",
                        "answer": "SAI", "hops": 2, "relation": "SAME_PROVINCE"
                    })
                    same_prov_false_count += 1
    
    # ==================== MCQ ====================
    
    all_clubs = [r['club'] for r in query("MATCH (c:Club) RETURN c.name as club") if r['club']]
    all_provinces = [r['province'] for r in query("MATCH (p:Province) RETURN p.name as province") if r['province']]
    
    # MCQ: Player -> Club
    logger.info("MCQ Player-Club...")
    result = query(f"MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) WITH p, collect(DISTINCT c.name) as clubs WHERE size(clubs) > 0 RETURN p.name as player, clubs[0] as correct ORDER BY rand() LIMIT {per_type_mcq*2}")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('type') == 'mcq' and q.get('relation') == 'PLAYED_FOR']) >= per_type_mcq:
            break
        if not r['player'] or not r['correct'] or r['player'] in seen:
            continue
        seen.add(r['player'])
        wrong = [c for c in all_clubs if c != r['correct']]
        if len(wrong) < 3:
            continue
        choices = [r['correct']] + random.sample(wrong, 3)
        random.shuffle(choices)
        questions.append({
            "type": "mcq", "question": f"{r['player']} đã chơi cho câu lạc bộ nào?",
            "choices": choices, "answer": r['correct'], "hops": 1, "relation": "PLAYED_FOR"
        })
    
    # MCQ: Player -> Province
    logger.info("MCQ Player-Province...")
    result = query(f"MATCH (p:Player)-[:BORN_IN]->(pr:Province) RETURN p.name as player, pr.name as correct ORDER BY rand() LIMIT {per_type_mcq*2}")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('type') == 'mcq' and q.get('relation') == 'BORN_IN']) >= per_type_mcq:
            break
        if not r['player'] or not r['correct'] or r['player'] in seen:
            continue
        seen.add(r['player'])
        wrong = [p for p in all_provinces if p != r['correct']]
        if len(wrong) < 3:
            continue
        choices = [r['correct']] + random.sample(wrong, 3)
        random.shuffle(choices)
        questions.append({
            "type": "mcq", "question": f"{r['player']} sinh ra ở tỉnh nào?",
            "choices": choices, "answer": r['correct'], "hops": 1, "relation": "BORN_IN"
        })
    
    # MCQ: Coach -> Club
    logger.info("MCQ Coach-Club...")
    result = query(f"MATCH (co:Coach)-[:COACHED]->(c:Club) WITH co, collect(DISTINCT c.name) as clubs WHERE size(clubs) > 0 RETURN co.name as coach, clubs[0] as correct ORDER BY rand() LIMIT {per_type_mcq*2}")
    seen = set()
    for r in result:
        if len([q for q in questions if q.get('type') == 'mcq' and q.get('relation') == 'COACHED']) >= per_type_mcq:
            break
        if not r['coach'] or not r['correct'] or r['coach'] in seen:
            continue
        seen.add(r['coach'])
        wrong = [c for c in all_clubs if c != r['correct']]
        if len(wrong) < 3:
            continue
        choices = [r['correct']] + random.sample(wrong, 3)
        random.shuffle(choices)
        questions.append({
            "type": "mcq", "question": f"{r['coach']} đã huấn luyện câu lạc bộ nào?",
            "choices": choices, "answer": r['correct'], "hops": 1, "relation": "COACHED"
        })
    
    # Shuffle và đánh số ID
    random.shuffle(questions)
    for i, q in enumerate(questions):
        q['id'] = i + 1
    
    # Thống kê
    yn = sum(1 for q in questions if q['type'] == 'yes_no')
    mcq = sum(1 for q in questions if q['type'] == 'mcq')
    dung = sum(1 for q in questions if q.get('answer') == 'ĐÚNG')
    sai = sum(1 for q in questions if q.get('answer') == 'SAI')
    h1 = sum(1 for q in questions if q.get('hops') == 1)
    h2 = sum(1 for q in questions if q.get('hops') == 2)
    
    logger.info(f"Total: {len(questions)} questions")
    logger.info(f"  Yes/No: {yn} (ĐÚNG: {dung}, SAI: {sai})")
    logger.info(f"  MCQ: {mcq}")
    logger.info(f"  1-hop: {h1}, 2-hop: {h2}")
    
    return questions


def save_questions(questions: List[Dict], filepath: str):
    """Lưu câu hỏi ra file."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved to {filepath}")


def main():
    questions = generate_questions(2200)
    save_questions(questions, "data/evaluation/eval_dataset.json")
    
    print("\n=== SAMPLE ===")
    for q in questions[:5]:
        print(f"\n[{q['id']}] {q['type']} | {q['hops']}-hop")
        print(f"Q: {q['question']}")
        if q['type'] == 'mcq':
            for i, c in enumerate(q['choices']):
                m = '✓' if c == q['answer'] else ' '
                print(f"  {m} {chr(65+i)}. {c}")
        else:
            print(f"A: {q['answer']}")

if __name__ == "__main__":
    main()
