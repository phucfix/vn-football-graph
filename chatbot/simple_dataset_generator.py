"""
Simple Evaluation Dataset Generator

Tạo câu hỏi đánh giá đơn giản, chính xác dựa trên dữ liệu thực trong KG.
Chỉ tạo 3 loại câu hỏi:
1. TRUE/FALSE - Mệnh đề đúng hoặc sai
2. YES/NO - Câu hỏi có/không
3. MCQ - Trắc nghiệm 4 lựa chọn
"""

import json
import random
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from chatbot.knowledge_graph import KnowledgeGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleDatasetGenerator:
    """Tạo tập câu hỏi đánh giá đơn giản."""
    
    def __init__(self):
        self.kg = KnowledgeGraph()
        self.kg.connect()
        
        # Cache dữ liệu
        self.players = []
        self.clubs = []
        self.provinces = []
        self.coaches = []
        self.national_teams = []
        
        # Quan hệ
        self.player_clubs = {}  # player -> [clubs]
        self.player_provinces = {}  # player -> province
        self.player_national = {}  # player -> [national teams]
        self.club_provinces = {}  # club -> province
        self.coach_clubs = {}  # coach -> [clubs]
        self.coach_national = {}  # coach -> [national teams]
        
    def load_data(self):
        """Tải dữ liệu từ KG."""
        logger.info("Loading data from KG...")
        
        # Lấy danh sách entities
        self.players = [r["name"] for r in self.kg.execute_cypher(
            "MATCH (p:Player) RETURN p.name as name"
        ) if r["name"]]
        
        self.clubs = [r["name"] for r in self.kg.execute_cypher(
            "MATCH (c:Club) RETURN c.name as name"
        ) if r["name"]]
        
        self.provinces = [r["name"] for r in self.kg.execute_cypher(
            "MATCH (p:Province) RETURN p.name as name"
        ) if r["name"]]
        
        self.coaches = [r["name"] for r in self.kg.execute_cypher(
            "MATCH (c:Coach) RETURN c.name as name"
        ) if r["name"]]
        
        self.national_teams = [r["name"] for r in self.kg.execute_cypher(
            "MATCH (nt:NationalTeam) RETURN nt.name as name"
        ) if r["name"]]
        
        logger.info(f"Loaded: {len(self.players)} players, {len(self.clubs)} clubs, "
                   f"{len(self.provinces)} provinces, {len(self.coaches)} coaches")
        
        # Lấy quan hệ Player -> Club
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) RETURN p.name as player, c.name as club"
        ):
            if r["player"] and r["club"]:
                self.player_clubs.setdefault(r["player"], []).append(r["club"])
        
        # Lấy quan hệ Player -> Province
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:BORN_IN]->(pr:Province) RETURN p.name as player, pr.name as province"
        ):
            if r["player"] and r["province"]:
                self.player_provinces[r["player"]] = r["province"]
        
        # Lấy quan hệ Player -> National Team
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:PLAYED_FOR_NATIONAL]->(nt:NationalTeam) RETURN p.name as player, nt.name as team"
        ):
            if r["player"] and r["team"]:
                self.player_national.setdefault(r["player"], []).append(r["team"])
        
        # Lấy quan hệ Club -> Province
        for r in self.kg.execute_cypher(
            "MATCH (c:Club)-[:BASED_IN]->(pr:Province) RETURN c.name as club, pr.name as province"
        ):
            if r["club"] and r["province"]:
                self.club_provinces[r["club"]] = r["province"]
        
        # Lấy quan hệ Coach -> Club
        for r in self.kg.execute_cypher(
            "MATCH (co:Coach)-[:COACHED]->(c:Club) RETURN co.name as coach, c.name as club"
        ):
            if r["coach"] and r["club"]:
                self.coach_clubs.setdefault(r["coach"], []).append(r["club"])
        
        # Lấy quan hệ Coach -> National Team
        for r in self.kg.execute_cypher(
            "MATCH (co:Coach)-[:COACHED_NATIONAL]->(nt:NationalTeam) RETURN co.name as coach, nt.name as team"
        ):
            if r["coach"] and r["team"]:
                self.coach_national.setdefault(r["coach"], []).append(r["team"])
        
        logger.info(f"Loaded relationships: {len(self.player_clubs)} player-club, "
                   f"{len(self.player_provinces)} player-province, "
                   f"{len(self.coach_clubs)} coach-club")
    
    # ==================== TRUE/FALSE QUESTIONS ====================
    
    def gen_tf_player_club_true(self) -> Dict:
        """Tạo câu TRUE: [Player] chơi cho [Club]."""
        players_with_clubs = [p for p in self.players if p in self.player_clubs]
        if not players_with_clubs:
            return None
            
        player = random.choice(players_with_clubs)
        club = random.choice(self.player_clubs[player])
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {player} đã chơi cho {club}.",
            "statement": f"{player} đã chơi cho {club}",
            "answer": "TRUE",
            "category": "player_club",
            "entities": [player, club]
        }
    
    def gen_tf_player_club_false(self) -> Dict:
        """Tạo câu FALSE: [Player] KHÔNG chơi cho [Club]."""
        players_with_clubs = [p for p in self.players if p in self.player_clubs]
        if not players_with_clubs:
            return None
            
        player = random.choice(players_with_clubs)
        player_clubs = set(self.player_clubs[player])
        other_clubs = [c for c in self.clubs if c not in player_clubs]
        
        if not other_clubs:
            return None
            
        club = random.choice(other_clubs)
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {player} đã chơi cho {club}.",
            "statement": f"{player} đã chơi cho {club}",
            "answer": "FALSE",
            "category": "player_club",
            "entities": [player, club]
        }
    
    def gen_tf_player_province_true(self) -> Dict:
        """Tạo câu TRUE: [Player] sinh ra ở [Province]."""
        if not self.player_provinces:
            return None
            
        player = random.choice(list(self.player_provinces.keys()))
        province = self.player_provinces[player]
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {player} sinh ra ở {province}.",
            "statement": f"{player} sinh ra ở {province}",
            "answer": "TRUE",
            "category": "player_province",
            "entities": [player, province]
        }
    
    def gen_tf_player_province_false(self) -> Dict:
        """Tạo câu FALSE: [Player] KHÔNG sinh ra ở [Province]."""
        if not self.player_provinces:
            return None
            
        player = random.choice(list(self.player_provinces.keys()))
        actual_province = self.player_provinces[player]
        other_provinces = [p for p in self.provinces if p != actual_province]
        
        if not other_provinces:
            return None
            
        province = random.choice(other_provinces)
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {player} sinh ra ở {province}.",
            "statement": f"{player} sinh ra ở {province}",
            "answer": "FALSE",
            "category": "player_province",
            "entities": [player, province]
        }
    
    def gen_tf_players_same_club_true(self) -> Dict:
        """Tạo câu TRUE: 2 cầu thủ cùng CLB."""
        # Tìm 2 cầu thủ có cùng CLB
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player)
            WHERE p1.name < p2.name
            RETURN p1.name as p1, p2.name as p2, c.name as club
            LIMIT 500
        """)
        
        if not result:
            return None
            
        r = random.choice(result)
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {r['p1']} và {r['p2']} cùng chơi cho một câu lạc bộ.",
            "statement": f"{r['p1']} và {r['p2']} cùng chơi cho một câu lạc bộ",
            "answer": "TRUE",
            "category": "players_same_club",
            "hops": 2,
            "entities": [r['p1'], r['p2'], r['club']]
        }
    
    def gen_tf_players_same_club_false(self) -> Dict:
        """Tạo câu FALSE: 2 cầu thủ KHÔNG cùng CLB."""
        # Tìm 2 cầu thủ không có CLB chung
        players_with_clubs = [p for p in self.players if p in self.player_clubs]
        
        if len(players_with_clubs) < 2:
            return None
        
        # Thử tối đa 50 lần
        for _ in range(50):
            p1, p2 = random.sample(players_with_clubs, 2)
            clubs1 = set(self.player_clubs.get(p1, []))
            clubs2 = set(self.player_clubs.get(p2, []))
            
            if not clubs1.intersection(clubs2):
                return {
                    "type": "true_false",
                    "question": f"Đúng hay sai: {p1} và {p2} cùng chơi cho một câu lạc bộ.",
                    "statement": f"{p1} và {p2} cùng chơi cho một câu lạc bộ",
                    "answer": "FALSE",
                    "category": "players_same_club",
                    "hops": 2,
                    "entities": [p1, p2]
                }
        return None
    
    def gen_tf_players_same_province_true(self) -> Dict:
        """Tạo câu TRUE: 2 cầu thủ cùng quê."""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:BORN_IN]->(pr:Province)<-[:BORN_IN]-(p2:Player)
            WHERE p1.name < p2.name
            RETURN p1.name as p1, p2.name as p2, pr.name as province
            LIMIT 500
        """)
        
        if not result:
            return None
            
        r = random.choice(result)
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {r['p1']} và {r['p2']} cùng quê.",
            "statement": f"{r['p1']} và {r['p2']} cùng quê",
            "answer": "TRUE",
            "category": "players_same_province",
            "hops": 2,
            "entities": [r['p1'], r['p2'], r['province']]
        }
    
    def gen_tf_players_same_province_false(self) -> Dict:
        """Tạo câu FALSE: 2 cầu thủ KHÔNG cùng quê."""
        players_with_provinces = list(self.player_provinces.keys())
        
        if len(players_with_provinces) < 2:
            return None
        
        for _ in range(50):
            p1, p2 = random.sample(players_with_provinces, 2)
            prov1 = self.player_provinces.get(p1)
            prov2 = self.player_provinces.get(p2)
            
            if prov1 and prov2 and prov1 != prov2:
                return {
                    "type": "true_false",
                    "question": f"Đúng hay sai: {p1} và {p2} cùng quê.",
                    "statement": f"{p1} và {p2} cùng quê",
                    "answer": "FALSE",
                    "category": "players_same_province",
                    "hops": 2,
                    "entities": [p1, p2]
                }
        return None
    
    def gen_tf_coach_club_true(self) -> Dict:
        """Tạo câu TRUE: [Coach] huấn luyện [Club]."""
        coaches_with_clubs = [c for c in self.coaches if c in self.coach_clubs]
        if not coaches_with_clubs:
            return None
            
        coach = random.choice(coaches_with_clubs)
        club = random.choice(self.coach_clubs[coach])
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {coach} đã huấn luyện {club}.",
            "statement": f"{coach} đã huấn luyện {club}",
            "answer": "TRUE",
            "category": "coach_club",
            "entities": [coach, club]
        }
    
    def gen_tf_coach_club_false(self) -> Dict:
        """Tạo câu FALSE: [Coach] KHÔNG huấn luyện [Club]."""
        coaches_with_clubs = [c for c in self.coaches if c in self.coach_clubs]
        if not coaches_with_clubs:
            return None
            
        coach = random.choice(coaches_with_clubs)
        coach_clubs = set(self.coach_clubs[coach])
        other_clubs = [c for c in self.clubs if c not in coach_clubs]
        
        if not other_clubs:
            return None
            
        club = random.choice(other_clubs)
        
        return {
            "type": "true_false",
            "question": f"Đúng hay sai: {coach} đã huấn luyện {club}.",
            "statement": f"{coach} đã huấn luyện {club}",
            "answer": "FALSE",
            "category": "coach_club",
            "entities": [coach, club]
        }
    
    # ==================== YES/NO QUESTIONS ====================
    
    def gen_yn_player_club_yes(self) -> Dict:
        """Tạo câu YES: [Player] có chơi cho [Club] không?"""
        players_with_clubs = [p for p in self.players if p in self.player_clubs]
        if not players_with_clubs:
            return None
            
        player = random.choice(players_with_clubs)
        club = random.choice(self.player_clubs[player])
        
        return {
            "type": "yes_no",
            "question": f"{player} có chơi cho {club} không?",
            "answer": "YES",
            "category": "player_club",
            "entities": [player, club]
        }
    
    def gen_yn_player_club_no(self) -> Dict:
        """Tạo câu NO: [Player] có chơi cho [Club] không? (thực tế không)"""
        players_with_clubs = [p for p in self.players if p in self.player_clubs]
        if not players_with_clubs:
            return None
            
        player = random.choice(players_with_clubs)
        player_clubs = set(self.player_clubs[player])
        other_clubs = [c for c in self.clubs if c not in player_clubs]
        
        if not other_clubs:
            return None
            
        club = random.choice(other_clubs)
        
        return {
            "type": "yes_no",
            "question": f"{player} có chơi cho {club} không?",
            "answer": "NO",
            "category": "player_club",
            "entities": [player, club]
        }
    
    def gen_yn_player_province_yes(self) -> Dict:
        """Tạo câu YES: [Player] có sinh ra ở [Province] không?"""
        if not self.player_provinces:
            return None
            
        player = random.choice(list(self.player_provinces.keys()))
        province = self.player_provinces[player]
        
        return {
            "type": "yes_no",
            "question": f"{player} có sinh ra ở {province} không?",
            "answer": "YES",
            "category": "player_province",
            "entities": [player, province]
        }
    
    def gen_yn_player_province_no(self) -> Dict:
        """Tạo câu NO: [Player] có sinh ra ở [Province] không? (thực tế không)"""
        if not self.player_provinces:
            return None
            
        player = random.choice(list(self.player_provinces.keys()))
        actual_province = self.player_provinces[player]
        other_provinces = [p for p in self.provinces if p != actual_province]
        
        if not other_provinces:
            return None
            
        province = random.choice(other_provinces)
        
        return {
            "type": "yes_no",
            "question": f"{player} có sinh ra ở {province} không?",
            "answer": "NO",
            "category": "player_province",
            "entities": [player, province]
        }
    
    def gen_yn_players_same_club_yes(self) -> Dict:
        """Tạo câu YES: 2 cầu thủ có cùng CLB không?"""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player)
            WHERE p1.name < p2.name
            RETURN p1.name as p1, p2.name as p2
            LIMIT 500
        """)
        
        if not result:
            return None
            
        r = random.choice(result)
        
        return {
            "type": "yes_no",
            "question": f"{r['p1']} và {r['p2']} có cùng câu lạc bộ không?",
            "answer": "YES",
            "category": "players_same_club",
            "hops": 2,
            "entities": [r['p1'], r['p2']]
        }
    
    def gen_yn_players_same_club_no(self) -> Dict:
        """Tạo câu NO: 2 cầu thủ có cùng CLB không? (thực tế không)"""
        players_with_clubs = [p for p in self.players if p in self.player_clubs]
        
        if len(players_with_clubs) < 2:
            return None
        
        for _ in range(50):
            p1, p2 = random.sample(players_with_clubs, 2)
            clubs1 = set(self.player_clubs.get(p1, []))
            clubs2 = set(self.player_clubs.get(p2, []))
            
            if not clubs1.intersection(clubs2):
                return {
                    "type": "yes_no",
                    "question": f"{p1} và {p2} có cùng câu lạc bộ không?",
                    "answer": "NO",
                    "category": "players_same_club",
                    "hops": 2,
                    "entities": [p1, p2]
                }
        return None
    
    def gen_yn_players_same_province_yes(self) -> Dict:
        """Tạo câu YES: 2 cầu thủ có cùng quê không?"""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:BORN_IN]->(pr:Province)<-[:BORN_IN]-(p2:Player)
            WHERE p1.name < p2.name
            RETURN p1.name as p1, p2.name as p2
            LIMIT 500
        """)
        
        if not result:
            return None
            
        r = random.choice(result)
        
        return {
            "type": "yes_no",
            "question": f"{r['p1']} và {r['p2']} có cùng quê không?",
            "answer": "YES",
            "category": "players_same_province",
            "hops": 2,
            "entities": [r['p1'], r['p2']]
        }
    
    def gen_yn_players_same_province_no(self) -> Dict:
        """Tạo câu NO: 2 cầu thủ có cùng quê không? (thực tế không)"""
        players_with_provinces = list(self.player_provinces.keys())
        
        if len(players_with_provinces) < 2:
            return None
        
        for _ in range(50):
            p1, p2 = random.sample(players_with_provinces, 2)
            prov1 = self.player_provinces.get(p1)
            prov2 = self.player_provinces.get(p2)
            
            if prov1 and prov2 and prov1 != prov2:
                return {
                    "type": "yes_no",
                    "question": f"{p1} và {p2} có cùng quê không?",
                    "answer": "NO",
                    "category": "players_same_province",
                    "hops": 2,
                    "entities": [p1, p2]
                }
        return None
    
    # ==================== MCQ QUESTIONS ====================
    
    def gen_mcq_player_club(self) -> Dict:
        """Tạo MCQ: [Player] chơi cho CLB nào?"""
        players_with_clubs = [p for p in self.players if p in self.player_clubs]
        if not players_with_clubs:
            return None
            
        player = random.choice(players_with_clubs)
        correct_club = random.choice(self.player_clubs[player])
        
        # Tạo 3 đáp án sai
        player_clubs = set(self.player_clubs[player])
        wrong_clubs = [c for c in self.clubs if c not in player_clubs]
        
        if len(wrong_clubs) < 3:
            return None
            
        wrong_choices = random.sample(wrong_clubs, 3)
        
        choices = [correct_club] + wrong_choices
        random.shuffle(choices)
        
        return {
            "type": "mcq",
            "question": f"{player} đã chơi cho câu lạc bộ nào?",
            "choices": choices,
            "answer": correct_club,
            "category": "player_club",
            "entities": [player]
        }
    
    def gen_mcq_player_province(self) -> Dict:
        """Tạo MCQ: [Player] sinh ra ở tỉnh nào?"""
        if not self.player_provinces:
            return None
            
        player = random.choice(list(self.player_provinces.keys()))
        correct_province = self.player_provinces[player]
        
        wrong_provinces = [p for p in self.provinces if p != correct_province]
        
        if len(wrong_provinces) < 3:
            return None
            
        wrong_choices = random.sample(wrong_provinces, 3)
        
        choices = [correct_province] + wrong_choices
        random.shuffle(choices)
        
        return {
            "type": "mcq",
            "question": f"{player} sinh ra ở tỉnh nào?",
            "choices": choices,
            "answer": correct_province,
            "category": "player_province",
            "entities": [player]
        }
    
    def gen_mcq_coach_club(self) -> Dict:
        """Tạo MCQ: [Coach] đã huấn luyện CLB nào?"""
        coaches_with_clubs = [c for c in self.coaches if c in self.coach_clubs]
        if not coaches_with_clubs:
            return None
            
        coach = random.choice(coaches_with_clubs)
        correct_club = random.choice(self.coach_clubs[coach])
        
        coach_clubs = set(self.coach_clubs[coach])
        wrong_clubs = [c for c in self.clubs if c not in coach_clubs]
        
        if len(wrong_clubs) < 3:
            return None
            
        wrong_choices = random.sample(wrong_clubs, 3)
        
        choices = [correct_club] + wrong_choices
        random.shuffle(choices)
        
        return {
            "type": "mcq",
            "question": f"{coach} đã huấn luyện câu lạc bộ nào?",
            "choices": choices,
            "answer": correct_club,
            "category": "coach_club",
            "entities": [coach]
        }
    
    def gen_mcq_club_province(self) -> Dict:
        """Tạo MCQ: [Club] đặt trụ sở ở tỉnh nào?"""
        if not self.club_provinces:
            return None
            
        club = random.choice(list(self.club_provinces.keys()))
        correct_province = self.club_provinces[club]
        
        wrong_provinces = [p for p in self.provinces if p != correct_province]
        
        if len(wrong_provinces) < 3:
            return None
            
        wrong_choices = random.sample(wrong_provinces, 3)
        
        choices = [correct_province] + wrong_choices
        random.shuffle(choices)
        
        return {
            "type": "mcq",
            "question": f"{club} đặt trụ sở ở tỉnh nào?",
            "choices": choices,
            "answer": correct_province,
            "category": "club_province",
            "entities": [club]
        }
    
    # ==================== GENERATE DATASET ====================
    
    def generate(self, num_questions: int = 2000) -> List[Dict]:
        """
        Tạo tập câu hỏi đánh giá.
        
        Phân bổ:
        - TRUE/FALSE: 40% (cân bằng TRUE và FALSE)
        - YES/NO: 30% (cân bằng YES và NO)
        - MCQ: 30%
        
        Trong đó:
        - 1-hop: 60%
        - 2-hop: 40% (cùng CLB, cùng quê)
        """
        self.load_data()
        
        questions = []
        
        # Số lượng mỗi loại
        n_tf = int(num_questions * 0.4)  # 40% T/F
        n_yn = int(num_questions * 0.3)  # 30% Y/N
        n_mcq = num_questions - n_tf - n_yn  # 30% MCQ
        
        # TRUE/FALSE generators (cân bằng TRUE và FALSE)
        tf_generators_true = [
            self.gen_tf_player_club_true,
            self.gen_tf_player_province_true,
            self.gen_tf_players_same_club_true,
            self.gen_tf_players_same_province_true,
            self.gen_tf_coach_club_true,
        ]
        
        tf_generators_false = [
            self.gen_tf_player_club_false,
            self.gen_tf_player_province_false,
            self.gen_tf_players_same_club_false,
            self.gen_tf_players_same_province_false,
            self.gen_tf_coach_club_false,
        ]
        
        # YES/NO generators (cân bằng YES và NO)
        yn_generators_yes = [
            self.gen_yn_player_club_yes,
            self.gen_yn_player_province_yes,
            self.gen_yn_players_same_club_yes,
            self.gen_yn_players_same_province_yes,
        ]
        
        yn_generators_no = [
            self.gen_yn_player_club_no,
            self.gen_yn_player_province_no,
            self.gen_yn_players_same_club_no,
            self.gen_yn_players_same_province_no,
        ]
        
        # MCQ generators
        mcq_generators = [
            self.gen_mcq_player_club,
            self.gen_mcq_player_province,
            self.gen_mcq_coach_club,
            self.gen_mcq_club_province,
        ]
        
        logger.info(f"Generating {n_tf} T/F, {n_yn} Y/N, {n_mcq} MCQ questions...")
        
        # Generate TRUE/FALSE (50% TRUE, 50% FALSE)
        n_true = n_tf // 2
        n_false = n_tf - n_true
        
        for i in range(n_true):
            gen = random.choice(tf_generators_true)
            q = gen()
            if q:
                q["id"] = len(questions) + 1
                questions.append(q)
        
        for i in range(n_false):
            gen = random.choice(tf_generators_false)
            q = gen()
            if q:
                q["id"] = len(questions) + 1
                questions.append(q)
        
        # Generate YES/NO (50% YES, 50% NO)
        n_yes = n_yn // 2
        n_no = n_yn - n_yes
        
        for i in range(n_yes):
            gen = random.choice(yn_generators_yes)
            q = gen()
            if q:
                q["id"] = len(questions) + 1
                questions.append(q)
        
        for i in range(n_no):
            gen = random.choice(yn_generators_no)
            q = gen()
            if q:
                q["id"] = len(questions) + 1
                questions.append(q)
        
        # Generate MCQ
        for i in range(n_mcq):
            gen = random.choice(mcq_generators)
            q = gen()
            if q:
                q["id"] = len(questions) + 1
                questions.append(q)
        
        # Shuffle
        random.shuffle(questions)
        
        # Re-assign IDs
        for i, q in enumerate(questions):
            q["id"] = i + 1
        
        logger.info(f"Generated {len(questions)} questions")
        
        # Stats
        tf_count = sum(1 for q in questions if q["type"] == "true_false")
        yn_count = sum(1 for q in questions if q["type"] == "yes_no")
        mcq_count = sum(1 for q in questions if q["type"] == "mcq")
        
        true_count = sum(1 for q in questions if q.get("answer") == "TRUE")
        false_count = sum(1 for q in questions if q.get("answer") == "FALSE")
        yes_count = sum(1 for q in questions if q.get("answer") == "YES")
        no_count = sum(1 for q in questions if q.get("answer") == "NO")
        
        hop2_count = sum(1 for q in questions if q.get("hops") == 2)
        
        logger.info(f"Distribution: T/F={tf_count}, Y/N={yn_count}, MCQ={mcq_count}")
        logger.info(f"T/F balance: TRUE={true_count}, FALSE={false_count}")
        logger.info(f"Y/N balance: YES={yes_count}, NO={no_count}")
        logger.info(f"Multi-hop (2-hop): {hop2_count}")
        
        return questions
    
    def save(self, questions: List[Dict], filepath: str):
        """Lưu tập câu hỏi ra file JSON."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(questions)} questions to {filepath}")


def main():
    """Generate evaluation dataset."""
    generator = SimpleDatasetGenerator()
    questions = generator.generate(num_questions=2200)
    generator.save(questions, "data/evaluation/simple_eval_dataset.json")
    
    # Print some examples
    print("\n=== SAMPLE QUESTIONS ===")
    for q in questions[:10]:
        print(f"\nID: {q['id']} | Type: {q['type']} | Category: {q['category']}")
        print(f"Q: {q['question']}")
        if q['type'] == 'mcq':
            for i, c in enumerate(q['choices']):
                marker = "✓" if c == q['answer'] else " "
                print(f"  {marker} {chr(65+i)}. {c}")
        else:
            print(f"A: {q['answer']}")


if __name__ == "__main__":
    main()
