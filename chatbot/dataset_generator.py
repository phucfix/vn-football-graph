"""
Dataset Generator cho Vietnamese Football Chatbot

Tạo 2000+ câu hỏi đánh giá với format:
- Câu hỏi Đúng/Sai (TRUE/FALSE) - 50%
- Câu hỏi trắc nghiệm 4 đáp án (MCQ) - 50%

Các loại suy luận:
- 1-hop: Truy vấn trực tiếp (Player->Club, Player->Province, ...)
- 2-hop: Suy luận qua 1 node trung gian (Player->Club<-Player)
- 3-hop: Suy luận qua 2 node trung gian
"""

import json
import random
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetGenerator:
    """Tạo dataset đánh giá chatbot."""
    
    def __init__(self):
        from chatbot.knowledge_graph import KnowledgeGraph
        self.kg = KnowledgeGraph()
        self.kg.connect()
        
        # Cache data
        self.data = {}
        
    def _load_data(self):
        """Load tất cả dữ liệu cần thiết từ KG."""
        logger.info("Loading data from KG...")
        
        # Players with clubs
        self.data['player_clubs'] = {}
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) RETURN p.name as player, c.name as club"
        ):
            if r['player'] and r['club']:
                self.data['player_clubs'].setdefault(r['player'], set()).add(r['club'])
        
        # Players with provinces
        self.data['player_provinces'] = {}
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:BORN_IN]->(pr:Province) RETURN p.name as player, pr.name as province"
        ):
            if r['player'] and r['province']:
                self.data['player_provinces'][r['player']] = r['province']
        
        # Players with national teams
        self.data['player_national'] = {}
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:PLAYED_FOR_NATIONAL]->(nt:NationalTeam) RETURN p.name as player, nt.name as team"
        ):
            if r['player'] and r['team']:
                self.data['player_national'].setdefault(r['player'], set()).add(r['team'])
        
        # Coaches with clubs
        self.data['coach_clubs'] = {}
        for r in self.kg.execute_cypher(
            "MATCH (co:Coach)-[:COACHED]->(c:Club) RETURN co.name as coach, c.name as club"
        ):
            if r['coach'] and r['club']:
                self.data['coach_clubs'].setdefault(r['coach'], set()).add(r['club'])
        
        # Clubs with provinces
        self.data['club_provinces'] = {}
        for r in self.kg.execute_cypher(
            "MATCH (c:Club)-[:BASED_IN]->(pr:Province) RETURN c.name as club, pr.name as province"
        ):
            if r['club'] and r['province']:
                self.data['club_provinces'][r['club']] = r['province']
        
        # All entities
        self.data['all_players'] = list(self.data['player_clubs'].keys())
        self.data['all_clubs'] = list(set(c for clubs in self.data['player_clubs'].values() for c in clubs))
        self.data['all_provinces'] = list(set(self.data['player_provinces'].values()) | set(self.data['club_provinces'].values()))
        self.data['all_coaches'] = list(self.data['coach_clubs'].keys())
        
        logger.info(f"Loaded: {len(self.data['all_players'])} players, {len(self.data['all_clubs'])} clubs, "
                   f"{len(self.data['all_provinces'])} provinces, {len(self.data['all_coaches'])} coaches")
    
    # ==================== 1-HOP QUESTIONS ====================
    
    def gen_1hop_player_club_true(self) -> Optional[Dict]:
        """[Player] đã chơi cho [Club] - TRUE"""
        players = [p for p in self.data['all_players'] if self.data['player_clubs'].get(p)]
        if not players:
            return None
        player = random.choice(players)
        club = random.choice(list(self.data['player_clubs'][player]))
        return {
            "question": f"{player} đã chơi cho {club}.",
            "answer": True,
            "hops": 1,
            "category": "player_club"
        }
    
    def gen_1hop_player_club_false(self) -> Optional[Dict]:
        """[Player] đã chơi cho [Club] - FALSE"""
        players = [p for p in self.data['all_players'] if self.data['player_clubs'].get(p)]
        if not players:
            return None
        player = random.choice(players)
        player_clubs = self.data['player_clubs'][player]
        other_clubs = [c for c in self.data['all_clubs'] if c not in player_clubs]
        if not other_clubs:
            return None
        club = random.choice(other_clubs)
        return {
            "question": f"{player} đã chơi cho {club}.",
            "answer": False,
            "hops": 1,
            "category": "player_club"
        }
    
    def gen_1hop_player_province_true(self) -> Optional[Dict]:
        """[Player] sinh ra ở [Province] - TRUE"""
        players = list(self.data['player_provinces'].keys())
        if not players:
            return None
        player = random.choice(players)
        province = self.data['player_provinces'][player]
        return {
            "question": f"{player} sinh ra ở {province}.",
            "answer": True,
            "hops": 1,
            "category": "player_province"
        }
    
    def gen_1hop_player_province_false(self) -> Optional[Dict]:
        """[Player] sinh ra ở [Province] - FALSE"""
        players = list(self.data['player_provinces'].keys())
        if not players:
            return None
        player = random.choice(players)
        actual = self.data['player_provinces'][player]
        others = [p for p in self.data['all_provinces'] if p != actual]
        if not others:
            return None
        province = random.choice(others)
        return {
            "question": f"{player} sinh ra ở {province}.",
            "answer": False,
            "hops": 1,
            "category": "player_province"
        }
    
    def gen_1hop_coach_club_true(self) -> Optional[Dict]:
        """[Coach] đã huấn luyện [Club] - TRUE"""
        coaches = [c for c in self.data['all_coaches'] if self.data['coach_clubs'].get(c)]
        if not coaches:
            return None
        coach = random.choice(coaches)
        club = random.choice(list(self.data['coach_clubs'][coach]))
        return {
            "question": f"{coach} đã huấn luyện {club}.",
            "answer": True,
            "hops": 1,
            "category": "coach_club"
        }
    
    def gen_1hop_coach_club_false(self) -> Optional[Dict]:
        """[Coach] đã huấn luyện [Club] - FALSE"""
        coaches = [c for c in self.data['all_coaches'] if self.data['coach_clubs'].get(c)]
        if not coaches:
            return None
        coach = random.choice(coaches)
        coach_clubs = self.data['coach_clubs'][coach]
        other_clubs = [c for c in self.data['all_clubs'] if c not in coach_clubs]
        if not other_clubs:
            return None
        club = random.choice(other_clubs)
        return {
            "question": f"{coach} đã huấn luyện {club}.",
            "answer": False,
            "hops": 1,
            "category": "coach_club"
        }
    
    # ==================== 2-HOP QUESTIONS ====================
    
    def gen_2hop_same_club_true(self) -> Optional[Dict]:
        """[Player1] và [Player2] từng chơi cùng CLB - TRUE"""
        # Tìm 2 cầu thủ cùng CLB
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player)
            WHERE p1.name < p2.name
            RETURN p1.name as p1, p2.name as p2
            LIMIT 1000
        """)
        if not result:
            return None
        r = random.choice(result)
        return {
            "question": f"{r['p1']} và {r['p2']} từng chơi cùng câu lạc bộ.",
            "answer": True,
            "hops": 2,
            "category": "same_club"
        }
    
    def gen_2hop_same_club_false(self) -> Optional[Dict]:
        """[Player1] và [Player2] từng chơi cùng CLB - FALSE"""
        players = [p for p in self.data['all_players'] if self.data['player_clubs'].get(p)]
        if len(players) < 2:
            return None
        
        for _ in range(20):
            p1, p2 = random.sample(players, 2)
            clubs1 = self.data['player_clubs'].get(p1, set())
            clubs2 = self.data['player_clubs'].get(p2, set())
            if not clubs1.intersection(clubs2):
                return {
                    "question": f"{p1} và {p2} từng chơi cùng câu lạc bộ.",
                    "answer": False,
                    "hops": 2,
                    "category": "same_club"
                }
        return None
    
    def gen_2hop_same_province_true(self) -> Optional[Dict]:
        """[Player1] và [Player2] cùng quê - TRUE"""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:BORN_IN]->(pr:Province)<-[:BORN_IN]-(p2:Player)
            WHERE p1.name < p2.name
            RETURN p1.name as p1, p2.name as p2
            LIMIT 1000
        """)
        if not result:
            return None
        r = random.choice(result)
        return {
            "question": f"{r['p1']} và {r['p2']} cùng quê.",
            "answer": True,
            "hops": 2,
            "category": "same_province"
        }
    
    def gen_2hop_same_province_false(self) -> Optional[Dict]:
        """[Player1] và [Player2] cùng quê - FALSE"""
        players = list(self.data['player_provinces'].keys())
        if len(players) < 2:
            return None
        
        for _ in range(20):
            p1, p2 = random.sample(players, 2)
            prov1 = self.data['player_provinces'].get(p1)
            prov2 = self.data['player_provinces'].get(p2)
            if prov1 and prov2 and prov1 != prov2:
                return {
                    "question": f"{p1} và {p2} cùng quê.",
                    "answer": False,
                    "hops": 2,
                    "category": "same_province"
                }
        return None
    
    # ==================== 3-HOP QUESTIONS ====================
    
    def gen_3hop_same_club_and_province_true(self) -> Optional[Dict]:
        """[Player1] và [Player2] vừa cùng CLB vừa cùng quê - TRUE"""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player),
                  (p1)-[:BORN_IN]->(pr:Province)<-[:BORN_IN]-(p2)
            WHERE p1.name < p2.name
            RETURN p1.name as p1, p2.name as p2
            LIMIT 500
        """)
        if not result:
            return None
        r = random.choice(result)
        return {
            "question": f"{r['p1']} và {r['p2']} vừa cùng câu lạc bộ vừa cùng quê.",
            "answer": True,
            "hops": 3,
            "category": "same_club_province"
        }
    
    def gen_3hop_same_club_and_province_false(self) -> Optional[Dict]:
        """[Player1] và [Player2] vừa cùng CLB vừa cùng quê - FALSE"""
        # Tìm 2 cầu thủ cùng CLB nhưng khác quê
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player),
                  (p1)-[:BORN_IN]->(pr1:Province),
                  (p2)-[:BORN_IN]->(pr2:Province)
            WHERE p1.name < p2.name AND pr1.name <> pr2.name
            RETURN p1.name as p1, p2.name as p2
            LIMIT 500
        """)
        if not result:
            return None
        r = random.choice(result)
        return {
            "question": f"{r['p1']} và {r['p2']} vừa cùng câu lạc bộ vừa cùng quê.",
            "answer": False,
            "hops": 3,
            "category": "same_club_province"
        }
    
    # ==================== MCQ QUESTIONS ====================
    
    def gen_mcq_player_club(self) -> Optional[Dict]:
        """[Player] đã chơi cho câu lạc bộ nào?"""
        players = [p for p in self.data['all_players'] if self.data['player_clubs'].get(p)]
        if not players:
            return None
        player = random.choice(players)
        correct = random.choice(list(self.data['player_clubs'][player]))
        
        # 3 đáp án sai
        wrong = [c for c in self.data['all_clubs'] if c not in self.data['player_clubs'][player]]
        if len(wrong) < 3:
            return None
        wrong_choices = random.sample(wrong, 3)
        
        choices = [correct] + wrong_choices
        random.shuffle(choices)
        
        return {
            "question": f"{player} đã chơi cho câu lạc bộ nào?",
            "choices": choices,
            "answer": correct,
            "hops": 1,
            "category": "mcq_player_club"
        }
    
    def gen_mcq_player_province(self) -> Optional[Dict]:
        """[Player] sinh ra ở tỉnh nào?"""
        players = list(self.data['player_provinces'].keys())
        if not players:
            return None
        player = random.choice(players)
        correct = self.data['player_provinces'][player]
        
        wrong = [p for p in self.data['all_provinces'] if p != correct]
        if len(wrong) < 3:
            return None
        wrong_choices = random.sample(wrong, 3)
        
        choices = [correct] + wrong_choices
        random.shuffle(choices)
        
        return {
            "question": f"{player} sinh ra ở tỉnh/thành phố nào?",
            "choices": choices,
            "answer": correct,
            "hops": 1,
            "category": "mcq_player_province"
        }
    
    def gen_mcq_coach_club(self) -> Optional[Dict]:
        """[Coach] đã huấn luyện câu lạc bộ nào?"""
        coaches = [c for c in self.data['all_coaches'] if self.data['coach_clubs'].get(c)]
        if not coaches:
            return None
        coach = random.choice(coaches)
        correct = random.choice(list(self.data['coach_clubs'][coach]))
        
        wrong = [c for c in self.data['all_clubs'] if c not in self.data['coach_clubs'][coach]]
        if len(wrong) < 3:
            return None
        wrong_choices = random.sample(wrong, 3)
        
        choices = [correct] + wrong_choices
        random.shuffle(choices)
        
        return {
            "question": f"{coach} đã huấn luyện câu lạc bộ nào?",
            "choices": choices,
            "answer": correct,
            "hops": 1,
            "category": "mcq_coach_club"
        }
    
    def gen_mcq_same_club(self) -> Optional[Dict]:
        """Ai từng chơi cùng CLB với [Player]?"""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player)
            WHERE p1.name <> p2.name
            RETURN p1.name as player, p2.name as teammate
            LIMIT 1000
        """)
        if not result:
            return None
        
        r = random.choice(result)
        player = r['player']
        correct = r['teammate']
        
        # Tìm người không cùng CLB
        player_clubs = self.data['player_clubs'].get(player, set())
        wrong = []
        for p in self.data['all_players']:
            if p != player and p != correct:
                p_clubs = self.data['player_clubs'].get(p, set())
                if not p_clubs.intersection(player_clubs):
                    wrong.append(p)
        
        if len(wrong) < 3:
            return None
        wrong_choices = random.sample(wrong, 3)
        
        choices = [correct] + wrong_choices
        random.shuffle(choices)
        
        return {
            "question": f"Ai từng chơi cùng câu lạc bộ với {player}?",
            "choices": choices,
            "answer": correct,
            "hops": 2,
            "category": "mcq_same_club"
        }
    
    # ==================== GENERATE DATASET ====================
    
    def generate(self, num_questions: int = 2200) -> List[Dict]:
        """Tạo dataset với phân bổ hợp lý."""
        self._load_data()
        
        questions = []
        
        # Phân bổ: 50% T/F, 50% MCQ
        n_tf = num_questions // 2
        n_mcq = num_questions - n_tf
        
        # T/F: 40% 1-hop, 40% 2-hop, 20% 3-hop
        n_tf_1hop = int(n_tf * 0.4)
        n_tf_2hop = int(n_tf * 0.4)
        n_tf_3hop = n_tf - n_tf_1hop - n_tf_2hop
        
        # Generators cho T/F
        tf_1hop_gens = [
            (self.gen_1hop_player_club_true, self.gen_1hop_player_club_false),
            (self.gen_1hop_player_province_true, self.gen_1hop_player_province_false),
            (self.gen_1hop_coach_club_true, self.gen_1hop_coach_club_false),
        ]
        
        tf_2hop_gens = [
            (self.gen_2hop_same_club_true, self.gen_2hop_same_club_false),
            (self.gen_2hop_same_province_true, self.gen_2hop_same_province_false),
        ]
        
        tf_3hop_gens = [
            (self.gen_3hop_same_club_and_province_true, self.gen_3hop_same_club_and_province_false),
        ]
        
        mcq_gens = [
            self.gen_mcq_player_club,
            self.gen_mcq_player_province,
            self.gen_mcq_coach_club,
            self.gen_mcq_same_club,
        ]
        
        logger.info(f"Generating {n_tf} T/F ({n_tf_1hop} 1-hop, {n_tf_2hop} 2-hop, {n_tf_3hop} 3-hop) "
                   f"and {n_mcq} MCQ questions...")
        
        # Generate T/F 1-hop (50% TRUE, 50% FALSE)
        for i in range(n_tf_1hop):
            gen_true, gen_false = random.choice(tf_1hop_gens)
            gen = gen_true if i % 2 == 0 else gen_false
            q = gen()
            if q:
                q['type'] = 'true_false'
                questions.append(q)
        
        # Generate T/F 2-hop
        for i in range(n_tf_2hop):
            gen_true, gen_false = random.choice(tf_2hop_gens)
            gen = gen_true if i % 2 == 0 else gen_false
            q = gen()
            if q:
                q['type'] = 'true_false'
                questions.append(q)
        
        # Generate T/F 3-hop
        for i in range(n_tf_3hop):
            gen_true, gen_false = random.choice(tf_3hop_gens)
            gen = gen_true if i % 2 == 0 else gen_false
            q = gen()
            if q:
                q['type'] = 'true_false'
                questions.append(q)
        
        # Generate MCQ
        for i in range(n_mcq):
            gen = random.choice(mcq_gens)
            q = gen()
            if q:
                q['type'] = 'mcq'
                questions.append(q)
        
        # Shuffle và assign IDs
        random.shuffle(questions)
        for i, q in enumerate(questions):
            q['id'] = i + 1
        
        # Stats
        self._print_stats(questions)
        
        return questions
    
    def _print_stats(self, questions: List[Dict]):
        """In thống kê dataset."""
        total = len(questions)
        tf = sum(1 for q in questions if q['type'] == 'true_false')
        mcq = sum(1 for q in questions if q['type'] == 'mcq')
        
        tf_true = sum(1 for q in questions if q['type'] == 'true_false' and q.get('answer') == True)
        tf_false = sum(1 for q in questions if q['type'] == 'true_false' and q.get('answer') == False)
        
        hop1 = sum(1 for q in questions if q.get('hops') == 1)
        hop2 = sum(1 for q in questions if q.get('hops') == 2)
        hop3 = sum(1 for q in questions if q.get('hops') == 3)
        
        logger.info(f"\n=== DATASET STATS ===")
        logger.info(f"Total: {total} questions")
        logger.info(f"T/F: {tf} (TRUE: {tf_true}, FALSE: {tf_false})")
        logger.info(f"MCQ: {mcq}")
        logger.info(f"1-hop: {hop1}, 2-hop: {hop2}, 3-hop: {hop3}")
        
        # By category
        cats = {}
        for q in questions:
            cat = q.get('category', 'unknown')
            cats[cat] = cats.get(cat, 0) + 1
        logger.info(f"Categories: {cats}")
    
    def save(self, questions: List[Dict], filepath: str):
        """Lưu dataset."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(questions)} questions to {filepath}")


def main():
    gen = DatasetGenerator()
    questions = gen.generate(2200)
    gen.save(questions, "data/evaluation/eval_dataset.json")
    
    # Print examples
    print("\n=== SAMPLE QUESTIONS ===")
    for q in questions[:10]:
        print(f"\n[{q['type'].upper()}] (hops={q['hops']}) {q['category']}")
        print(f"Q: {q['question']}")
        if q['type'] == 'mcq':
            for i, c in enumerate(q['choices']):
                mark = "✓" if c == q['answer'] else " "
                print(f"  {mark} {chr(65+i)}. {c}")
        else:
            print(f"A: {q['answer']}")


if __name__ == "__main__":
    main()
