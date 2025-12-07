"""
Graph Reasoning Chatbot

Chatbot sử dụng suy luận đồ thị để trả lời câu hỏi.
Hỗ trợ:
- Câu hỏi TRUE/FALSE
- Câu hỏi MCQ (trắc nghiệm)
"""

import logging
from typing import Tuple, List, Optional, Set
from .knowledge_graph import KnowledgeGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphReasoningChatbot:
    """Chatbot suy luận dựa trên đồ thị tri thức."""
    
    def __init__(self):
        self.kg = KnowledgeGraph()
        self._initialized = False
        
        # Cache để tăng tốc
        self._player_clubs = {}
        self._player_provinces = {}
        self._coach_clubs = {}
        self._club_provinces = {}
        
    def initialize(self) -> bool:
        """Khởi tạo chatbot."""
        try:
            self.kg.connect()
            self._load_cache()
            self._initialized = True
            logger.info("✅ GraphReasoningChatbot initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            return False
    
    def _load_cache(self):
        """Load cache để truy vấn nhanh hơn."""
        logger.info("Loading cache...")
        
        # Player -> Clubs
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) RETURN p.name as player, c.name as club"
        ):
            if r['player'] and r['club']:
                self._player_clubs.setdefault(r['player'], set()).add(r['club'])
        
        # Player -> Province
        for r in self.kg.execute_cypher(
            "MATCH (p:Player)-[:BORN_IN]->(pr:Province) RETURN p.name as player, pr.name as province"
        ):
            if r['player'] and r['province']:
                self._player_provinces[r['player']] = r['province']
        
        # Coach -> Clubs
        for r in self.kg.execute_cypher(
            "MATCH (co:Coach)-[:COACHED]->(c:Club) RETURN co.name as coach, c.name as club"
        ):
            if r['coach'] and r['club']:
                self._coach_clubs.setdefault(r['coach'], set()).add(r['club'])
        
        # Club -> Province
        for r in self.kg.execute_cypher(
            "MATCH (c:Club)-[:BASED_IN]->(pr:Province) RETURN c.name as club, pr.name as province"
        ):
            if r['club'] and r['province']:
                self._club_provinces[r['club']] = r['province']
        
        logger.info(f"Cache loaded: {len(self._player_clubs)} players, {len(self._coach_clubs)} coaches")
    
    # ==================== ENTITY EXTRACTION ====================
    
    def _normalize_name(self, full_name: str) -> List[str]:
        """Tạo các biến thể của tên để matching."""
        variants = [full_name.lower()]
        parts = full_name.split()
        if len(parts) >= 2:
            # Tên + tên đệm cuối: "Nguyễn Quang Hải" -> "Quang Hải"
            variants.append(" ".join(parts[1:]).lower())
            # Chỉ tên cuối: "Nguyễn Quang Hải" -> "Hải"
            variants.append(parts[-1].lower())
            # 2 từ cuối nếu có 3+ từ
            if len(parts) >= 3:
                variants.append(" ".join(parts[-2:]).lower())
        return variants
    
    def _find_player(self, text: str) -> Optional[str]:
        """Tìm tên cầu thủ trong text (hỗ trợ tên ngắn)."""
        text_lower = text.lower()
        all_players = set(self._player_clubs.keys()) | set(self._player_provinces.keys())
        
        # Ưu tiên match tên đầy đủ trước
        for player in all_players:
            if player.lower() in text_lower:
                return player
        
        # Thử match với tên ngắn
        for player in all_players:
            for variant in self._normalize_name(player):
                if len(variant) > 3 and variant in text_lower:
                    return player
        
        return None
    
    def _find_players(self, text: str) -> List[str]:
        """Tìm tất cả tên cầu thủ trong text (ưu tiên tên đầy đủ)."""
        text_lower = text.lower()
        all_players = set(self._player_clubs.keys()) | set(self._player_provinces.keys())
        
        # Bước 1: Tìm match tên đầy đủ
        found_full = []
        for player in all_players:
            if player.lower() in text_lower:
                found_full.append(player)
        
        # Nếu tìm được >= 2 cầu thủ bằng tên đầy đủ, dùng luôn
        if len(found_full) >= 2:
            return found_full[:2]  # Chỉ lấy 2 đầu tiên
        
        # Bước 2: Nếu chưa đủ, thử tìm bằng tên ngắn
        # Tìm các từ trong text có thể là tên cầu thủ
        found_short = set(found_full)
        
        # Thử match các tên 2 từ (VD: "Quang Hải", "Văn Hậu")
        for player in all_players:
            if player in found_short:
                continue
            variants = self._normalize_name(player)
            # Ưu tiên variant dài hơn (tên 2 từ)
            for variant in sorted(variants, key=len, reverse=True):
                if len(variant) > 5 and variant in text_lower:  # Ít nhất 6 ký tự
                    found_short.add(player)
                    break
        
        return list(found_short)[:2]  # Chỉ lấy tối đa 2 cầu thủ
    
    def _find_club(self, text: str) -> Optional[str]:
        """Tìm tên CLB trong text (hỗ trợ tên ngắn và viết tắt)."""
        text_lower = text.lower()
        all_clubs = set()
        for clubs in self._player_clubs.values():
            all_clubs.update(clubs)
        for clubs in self._coach_clubs.values():
            all_clubs.update(clubs)
        
        # Mapping các tên viết tắt phổ biến
        club_aliases = {
            'hagl': 'Câu lạc bộ bóng đá Hoàng Anh Gia Lai',
            'hoàng anh gia lai': 'Câu lạc bộ bóng đá Hoàng Anh Gia Lai',
            'hà nội fc': 'Câu lạc bộ bóng đá Hà Nội',
            'hà nội': 'Hà Nội',
            'nam định': 'Câu lạc bộ bóng đá Thép Xanh Nam Định',
            'viettel': 'Câu lạc bộ bóng đá Thể Công – Viettel',
            'slna': 'Câu lạc bộ bóng đá Sông Lam Nghệ An',
            'nghệ an': 'Câu lạc bộ bóng đá Sông Lam Nghệ An',
            'hải phòng': 'Câu lạc bộ bóng đá Hải Phòng',
            'đà nẵng': 'Câu lạc bộ bóng đá SHB Đà Nẵng',
            'cần thơ': 'Câu lạc bộ bóng đá Cần Thơ',
            'quảng nam': 'Câu lạc bộ bóng đá Quảng Nam',
            'sài gòn': 'Câu lạc bộ bóng đá Sài Gòn',
            'tp. hcm': 'Câu lạc bộ bóng đá Thành phố Hồ Chí Minh',
            'hồ chí minh': 'Câu lạc bộ bóng đá Thành phố Hồ Chí Minh',
            'bình dương': 'Becamex Thành phố Hồ Chí Minh',
            'đồng nai': 'Câu lạc bộ bóng đá Đồng Nai'
        }
        
        # Kiểm tra aliases trước
        for alias, full_name in club_aliases.items():
            if alias in text_lower and full_name in all_clubs:
                return full_name
        
        # Tên đầy đủ
        for club in all_clubs:
            if club.lower() in text_lower:
                return club
        
        # Tên ngắn (vd: "Hà Nội" trong "Câu lạc bộ bóng đá Hà Nội")
        for club in all_clubs:
            # Lấy phần cuối của tên CLB
            short_names = []
            if "câu lạc bộ bóng đá" in club.lower():
                short = club.lower().replace("câu lạc bộ bóng đá", "").strip()
                short_names.append(short)
            if "học viện" in club.lower():
                short_names.append(club.lower().replace("học viện bóng đá", "").strip())
            
            for short in short_names:
                if len(short) > 2 and short in text_lower:
                    return club
        
        return None
    
    def _find_province(self, text: str) -> Optional[str]:
        """Tìm tên tỉnh trong text."""
        text_lower = text.lower()
        all_provinces = set(self._player_provinces.values()) | set(self._club_provinces.values())
        for province in all_provinces:
            if province.lower() in text_lower:
                return province
        return None
    
    def _find_coach(self, text: str) -> Optional[str]:
        """Tìm tên HLV trong text."""
        text_lower = text.lower()
        for coach in self._coach_clubs.keys():
            if coach.lower() in text_lower:
                return coach
        return None
    
    # ==================== GRAPH QUERIES ====================
    
    def check_player_club(self, player: str, club: str) -> bool:
        """Kiểm tra cầu thủ có chơi cho CLB không."""
        clubs = self._player_clubs.get(player, set())
        for c in clubs:
            if c.lower() == club.lower() or c.lower() in club.lower() or club.lower() in c.lower():
                return True
        return False
    
    def check_player_province(self, player: str, province: str) -> bool:
        """Kiểm tra cầu thủ có sinh ra ở tỉnh không."""
        prov = self._player_provinces.get(player)
        if not prov:
            return False
        return prov.lower() == province.lower() or prov.lower() in province.lower() or province.lower() in prov.lower()
    
    def check_coach_club(self, coach: str, club: str) -> bool:
        """Kiểm tra HLV có huấn luyện CLB không."""
        clubs = self._coach_clubs.get(coach, set())
        for c in clubs:
            if c.lower() == club.lower() or c.lower() in club.lower() or club.lower() in c.lower():
                return True
        return False
    
    def check_same_club(self, player1: str, player2: str) -> bool:
        """Kiểm tra 2 cầu thủ có cùng CLB không."""
        clubs1 = self._player_clubs.get(player1, set())
        clubs2 = self._player_clubs.get(player2, set())
        return bool(clubs1 & clubs2)
    
    def check_same_province(self, player1: str, player2: str) -> bool:
        """Kiểm tra 2 cầu thủ có cùng quê không."""
        prov1 = self._player_provinces.get(player1)
        prov2 = self._player_provinces.get(player2)
        if not prov1 or not prov2:
            return False
        return prov1 == prov2
    
    def check_same_club_and_province(self, player1: str, player2: str) -> bool:
        """Kiểm tra 2 cầu thủ vừa cùng CLB vừa cùng quê."""
        return self.check_same_club(player1, player2) and self.check_same_province(player1, player2)
    
    def get_player_clubs(self, player: str) -> Set[str]:
        """Lấy danh sách CLB của cầu thủ."""
        return self._player_clubs.get(player, set())
    
    def get_player_province(self, player: str) -> Optional[str]:
        """Lấy quê của cầu thủ."""
        return self._player_provinces.get(player)
    
    def get_coach_clubs(self, coach: str) -> Set[str]:
        """Lấy danh sách CLB của HLV."""
        return self._coach_clubs.get(coach, set())
    
    def get_teammates(self, player: str) -> Set[str]:
        """Lấy danh sách đồng đội (cùng CLB)."""
        clubs = self._player_clubs.get(player, set())
        teammates = set()
        for p, p_clubs in self._player_clubs.items():
            if p != player and clubs & p_clubs:
                teammates.add(p)
        return teammates
    
    def get_club_province(self, club: str) -> Optional[str]:
        """Lấy tỉnh/thành phố của CLB."""
        return self._club_provinces.get(club)
    
    # ==================== QUESTION ANSWERING ====================
    
    def answer_true_false(self, statement: str) -> Tuple[bool, float]:
        """
        Trả lời câu hỏi TRUE/FALSE.
        
        Returns:
            (answer: bool, confidence: float)
        """
        s_lower = statement.lower()
        
        # Pattern: [Player] đã chơi cho [Club]
        if "đã chơi cho" in s_lower or "chơi cho" in s_lower or "thi đấu cho" in s_lower:
            player = self._find_player(statement)
            club = self._find_club(statement)
            if player and club:
                result = self.check_player_club(player, club)
                return result, 1.0
        
        # Pattern: [Player] có chơi cho [Club] không?
        if "có " in s_lower and " không" in s_lower and ("chơi cho" in s_lower or "thi đấu cho" in s_lower):
            player = self._find_player(statement)
            club = self._find_club(statement)
            if player and club:
                result = self.check_player_club(player, club)
                return result, 1.0
        
        # Pattern: [Player] sinh ra ở [Province]
        if "sinh ra" in s_lower or "quê" in s_lower:
            player = self._find_player(statement)
            province = self._find_province(statement)
            if player and province:
                result = self.check_player_province(player, province)
                return result, 1.0
        
        # Pattern: [Coach] đã huấn luyện [Club]
        if "huấn luyện" in s_lower:
            coach = self._find_coach(statement)
            club = self._find_club(statement)
            if coach and club:
                result = self.check_coach_club(coach, club)
                return result, 1.0
        
        # Pattern: [Player1] và [Player2] vừa cùng CLB vừa cùng quê
        if "vừa cùng" in s_lower:
            players = self._find_players(statement)
            if len(players) >= 2:
                result = self.check_same_club_and_province(players[0], players[1])
                return result, 1.0
        
        # Pattern: [Player1] và [Player2] từng chơi cùng CLB
        if " và " in statement and ("cùng câu lạc bộ" in s_lower or "cùng clb" in s_lower):
            players = self._find_players(statement)
            if len(players) >= 2:
                result = self.check_same_club(players[0], players[1])
                return result, 1.0
        
        # Pattern: [Player1] và [Player2] cùng quê
        if " và " in statement and "cùng quê" in s_lower:
            players = self._find_players(statement)
            if len(players) >= 2:
                result = self.check_same_province(players[0], players[1])
                return result, 1.0
        
        logger.warning(f"Cannot parse: {statement}")
        return False, 0.5
    
    def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float]:
        """
        Trả lời câu hỏi MCQ.
        
        Returns:
            (selected_choice: str, confidence: float)
        """
        q_lower = question.lower()
        
        # Pattern: [Player] đã chơi cho CLB nào?
        if "đã chơi cho" in q_lower and ("câu lạc bộ nào" in q_lower or "clb nào" in q_lower):
            player = self._find_player(question)
            if player:
                clubs = self.get_player_clubs(player)
                for choice in choices:
                    for club in clubs:
                        if club.lower() in choice.lower() or choice.lower() in club.lower():
                            return choice, 1.0
        
        # Pattern: [Player] chơi cho đội nào?
        if "chơi cho đội nào" in q_lower or "chơi cho đội" in q_lower:
            player = self._find_player(question)
            if player:
                clubs = self.get_player_clubs(player)
                for choice in choices:
                    # Strip A. B. C. D. prefixes
                    clean_choice = choice.split('.', 1)[-1].strip() if '.' in choice else choice
                    for club in clubs:
                        if club.lower() in clean_choice.lower() or clean_choice.lower() in club.lower():
                            return choice, 1.0
        
        # Pattern: [Player] sinh ra ở tỉnh nào?
        if "sinh ra" in q_lower and ("tỉnh" in q_lower or "thành phố" in q_lower):
            player = self._find_player(question)
            if player:
                province = self.get_player_province(player)
                if province:
                    for choice in choices:
                        if province.lower() in choice.lower() or choice.lower() in province.lower():
                            return choice, 1.0
        
        # Pattern: [Club] có trụ sở ở đâu?
        if "trụ sở ở đâu" in q_lower or "trụ sở" in q_lower:
            club = self._find_club(question)
            if club:
                province = self.get_club_province(club)
                if province:
                    for choice in choices:
                        # Strip A. B. C. D. prefixes
                        clean_choice = choice.split('.', 1)[-1].strip() if '.' in choice else choice
                        if province.lower() in clean_choice.lower() or clean_choice.lower() in province.lower():
                            return choice, 1.0
        
        # Pattern: [Coach] đã huấn luyện CLB nào?
        if "huấn luyện" in q_lower and ("câu lạc bộ nào" in q_lower or "clb nào" in q_lower):
            coach = self._find_coach(question)
            if coach:
                clubs = self.get_coach_clubs(coach)
                for choice in choices:
                    for club in clubs:
                        if club.lower() in choice.lower() or choice.lower() in club.lower():
                            return choice, 1.0
        
        # Pattern: Ai từng chơi cùng CLB với [Player]?
        if "từng chơi cùng" in q_lower or "cùng câu lạc bộ" in q_lower:
            player = self._find_player(question)
            if player:
                teammates = self.get_teammates(player)
                for choice in choices:
                    for teammate in teammates:
                        if teammate.lower() in choice.lower() or choice.lower() in teammate.lower():
                            return choice, 1.0
        
        # Pattern: [Player1] và [Player2] có cùng quê không?
        if " và " in question and "cùng quê" in q_lower and "không" in q_lower:
            players = self._find_players(question)
            if len(players) >= 2:
                result = self.check_same_province(players[0], players[1])
                # Convert boolean to MCQ answer
                if result:
                    for choice in choices:
                        clean_choice = choice.split('.', 1)[-1].strip() if '.' in choice else choice
                        if "có" in clean_choice.lower() or "yes" in clean_choice.lower():
                            return choice, 1.0
                else:
                    for choice in choices:
                        clean_choice = choice.split('.', 1)[-1].strip() if '.' in choice else choice
                        if "không" in clean_choice.lower() or "no" in clean_choice.lower():
                            return choice, 1.0
                        if teammate.lower() in choice.lower() or choice.lower() in teammate.lower():
                            return choice, 1.0
        
        logger.warning(f"Cannot parse MCQ: {question}")
        return choices[0], 0.3
