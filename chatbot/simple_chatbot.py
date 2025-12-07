"""
Simple Chatbot for Vietnamese Football Knowledge Graph

Chatbot đơn giản chỉ trả lời:
1. Câu hỏi Đúng/Sai (TRUE/FALSE)
2. Câu hỏi Có/Không (YES/NO)  
3. Câu hỏi trắc nghiệm (MCQ)

Dựa hoàn toàn vào Knowledge Graph, không suy luận phức tạp.
"""

import logging
from typing import Tuple, List, Optional
from .knowledge_graph import KnowledgeGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleKGChatbot:
    """
    Chatbot đơn giản dựa trên Knowledge Graph.
    Chỉ trả lời các câu hỏi có cấu trúc rõ ràng.
    """
    
    def __init__(self):
        self.kg = KnowledgeGraph()
        self._initialized = False
        
    def initialize(self) -> bool:
        """Khởi tạo kết nối đến Knowledge Graph."""
        try:
            self.kg.connect()
            self._initialized = True
            logger.info("✅ SimpleKGChatbot initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            return False
    
    # ==================== TRUY VẤN CƠ BẢN ====================
    
    def get_player_clubs(self, player_name: str) -> List[str]:
        """Lấy danh sách CLB mà cầu thủ đã chơi."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
            WHERE toLower(p.name) CONTAINS toLower($name)
            RETURN DISTINCT c.name as club
        """, {"name": player_name})
        return [r["club"] for r in result if r["club"]]
    
    def get_player_province(self, player_name: str) -> Optional[str]:
        """Lấy quê quán của cầu thủ."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:BORN_IN]->(pr:Province)
            WHERE toLower(p.name) CONTAINS toLower($name)
            RETURN pr.name as province
            LIMIT 1
        """, {"name": player_name})
        return result[0]["province"] if result else None
    
    def get_player_position(self, player_name: str) -> Optional[str]:
        """Lấy vị trí thi đấu của cầu thủ."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:HAS_POSITION]->(pos:Position)
            WHERE toLower(p.name) CONTAINS toLower($name)
            RETURN pos.name as position
            LIMIT 1
        """, {"name": player_name})
        return result[0]["position"] if result else None
    
    def get_player_national_team(self, player_name: str) -> List[str]:
        """Lấy đội tuyển quốc gia mà cầu thủ đã chơi."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:PLAYED_FOR_NATIONAL]->(nt:NationalTeam)
            WHERE toLower(p.name) CONTAINS toLower($name)
            RETURN DISTINCT nt.name as team
        """, {"name": player_name})
        return [r["team"] for r in result if r["team"]]
    
    def get_club_players(self, club_name: str) -> List[str]:
        """Lấy danh sách cầu thủ của CLB."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
            WHERE toLower(c.name) CONTAINS toLower($name)
            RETURN DISTINCT p.name as player
        """, {"name": club_name})
        return [r["player"] for r in result if r["player"]]
    
    def get_club_province(self, club_name: str) -> Optional[str]:
        """Lấy tỉnh/thành phố của CLB."""
        result = self.kg.execute_cypher("""
            MATCH (c:Club)-[:BASED_IN]->(pr:Province)
            WHERE toLower(c.name) CONTAINS toLower($name)
            RETURN pr.name as province
            LIMIT 1
        """, {"name": club_name})
        return result[0]["province"] if result else None
    
    def get_coach_teams(self, coach_name: str) -> List[str]:
        """Lấy danh sách đội bóng mà HLV đã huấn luyện."""
        result = self.kg.execute_cypher("""
            MATCH (co:Coach)-[:COACHED]->(c:Club)
            WHERE toLower(co.name) CONTAINS toLower($name)
            RETURN DISTINCT c.name as team
            UNION
            MATCH (co:Coach)-[:COACHED_NATIONAL]->(nt:NationalTeam)
            WHERE toLower(co.name) CONTAINS toLower($name)
            RETURN DISTINCT nt.name as team
        """, {"name": coach_name})
        return [r["team"] for r in result if r["team"]]
    
    def get_province_players(self, province_name: str) -> List[str]:
        """Lấy danh sách cầu thủ sinh ra ở tỉnh."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:BORN_IN]->(pr:Province)
            WHERE toLower(pr.name) CONTAINS toLower($name)
            RETURN DISTINCT p.name as player
        """, {"name": province_name})
        return [r["player"] for r in result if r["player"]]
    
    # ==================== KIỂM TRA QUAN HỆ ====================
    
    def check_player_played_for_club(self, player_name: str, club_name: str) -> bool:
        """Kiểm tra cầu thủ có chơi cho CLB không."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
            WHERE toLower(p.name) CONTAINS toLower($player)
              AND toLower(c.name) CONTAINS toLower($club)
            RETURN count(*) as cnt
        """, {"player": player_name, "club": club_name})
        return result[0]["cnt"] > 0 if result else False
    
    def check_player_born_in_province(self, player_name: str, province_name: str) -> bool:
        """Kiểm tra cầu thủ có sinh ra ở tỉnh không."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player)-[:BORN_IN]->(pr:Province)
            WHERE toLower(p.name) CONTAINS toLower($player)
              AND toLower(pr.name) CONTAINS toLower($province)
            RETURN count(*) as cnt
        """, {"player": player_name, "province": province_name})
        return result[0]["cnt"] > 0 if result else False
    
    def check_players_same_club(self, player1: str, player2: str) -> bool:
        """Kiểm tra 2 cầu thủ có cùng CLB không (từng chơi cho cùng 1 CLB)."""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player)
            WHERE toLower(p1.name) CONTAINS toLower($p1)
              AND toLower(p2.name) CONTAINS toLower($p2)
            RETURN count(*) as cnt
        """, {"p1": player1, "p2": player2})
        return result[0]["cnt"] > 0 if result else False
    
    def check_players_same_province(self, player1: str, player2: str) -> bool:
        """Kiểm tra 2 cầu thủ có cùng quê không."""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:BORN_IN]->(pr:Province)<-[:BORN_IN]-(p2:Player)
            WHERE toLower(p1.name) CONTAINS toLower($p1)
              AND toLower(p2.name) CONTAINS toLower($p2)
            RETURN count(*) as cnt
        """, {"p1": player1, "p2": player2})
        return result[0]["cnt"] > 0 if result else False
    
    def check_players_same_national_team(self, player1: str, player2: str) -> bool:
        """Kiểm tra 2 cầu thủ có cùng ĐTQG không."""
        result = self.kg.execute_cypher("""
            MATCH (p1:Player)-[:PLAYED_FOR_NATIONAL]->(nt:NationalTeam)<-[:PLAYED_FOR_NATIONAL]-(p2:Player)
            WHERE toLower(p1.name) CONTAINS toLower($p1)
              AND toLower(p2.name) CONTAINS toLower($p2)
            RETURN count(*) as cnt
        """, {"p1": player1, "p2": player2})
        return result[0]["cnt"] > 0 if result else False
    
    def check_coach_coached_club(self, coach_name: str, club_name: str) -> bool:
        """Kiểm tra HLV có huấn luyện CLB không."""
        result = self.kg.execute_cypher("""
            MATCH (co:Coach)-[:COACHED]->(c:Club)
            WHERE toLower(co.name) CONTAINS toLower($coach)
              AND toLower(c.name) CONTAINS toLower($club)
            RETURN count(*) as cnt
        """, {"coach": coach_name, "club": club_name})
        return result[0]["cnt"] > 0 if result else False
    
    def check_coach_coached_national(self, coach_name: str, team_name: str) -> bool:
        """Kiểm tra HLV có huấn luyện ĐTQG không."""
        result = self.kg.execute_cypher("""
            MATCH (co:Coach)-[:COACHED_NATIONAL]->(nt:NationalTeam)
            WHERE toLower(co.name) CONTAINS toLower($coach)
              AND toLower(nt.name) CONTAINS toLower($team)
            RETURN count(*) as cnt
        """, {"coach": coach_name, "team": team_name})
        return result[0]["cnt"] > 0 if result else False
    
    def check_club_in_province(self, club_name: str, province_name: str) -> bool:
        """Kiểm tra CLB có trụ sở ở tỉnh không."""
        result = self.kg.execute_cypher("""
            MATCH (c:Club)-[:BASED_IN]->(pr:Province)
            WHERE toLower(c.name) CONTAINS toLower($club)
              AND toLower(pr.name) CONTAINS toLower($province)
            RETURN count(*) as cnt
        """, {"club": club_name, "province": province_name})
        return result[0]["cnt"] > 0 if result else False
    
    # ==================== TRẢ LỜI CÂU HỎI ====================
    
    def answer_true_false(self, question: str, statement: str) -> Tuple[str, float]:
        """
        Trả lời câu hỏi TRUE/FALSE.
        
        Args:
            question: Câu hỏi gốc
            statement: Mệnh đề cần xác minh
            
        Returns:
            ("TRUE" hoặc "FALSE", confidence)
        """
        statement_lower = statement.lower()
        
        # Pattern 1: [Player] chơi cho [Club]
        if "chơi cho" in statement_lower or "thi đấu cho" in statement_lower or "khoác áo" in statement_lower:
            # Tìm tên cầu thủ và CLB
            parts = statement.split(" chơi cho " if " chơi cho " in statement else 
                                   " thi đấu cho " if " thi đấu cho " in statement else " khoác áo ")
            if len(parts) >= 2:
                player = parts[0].strip()
                club = parts[1].strip().rstrip(".")
                if self.check_player_played_for_club(player, club):
                    return "TRUE", 1.0
                return "FALSE", 1.0
        
        # Pattern 2: [Player] sinh ra ở/tại [Province]
        if "sinh ra" in statement_lower or "quê ở" in statement_lower or "đến từ" in statement_lower:
            for sep in [" sinh ra ở ", " sinh ra tại ", " quê ở ", " quê tại ", " đến từ "]:
                if sep in statement.lower():
                    idx = statement.lower().find(sep)
                    player = statement[:idx].strip()
                    province = statement[idx + len(sep):].strip().rstrip(".")
                    if self.check_player_born_in_province(player, province):
                        return "TRUE", 1.0
                    return "FALSE", 1.0
        
        # Pattern 3: [Player1] và [Player2] cùng CLB/quê/ĐTQG
        if " và " in statement and ("cùng" in statement_lower):
            parts = statement.split(" và ")
            if len(parts) >= 2:
                player1 = parts[0].strip()
                rest = parts[1]
                
                # Tìm player2 (trước "cùng")
                if " cùng " in rest.lower():
                    idx = rest.lower().find(" cùng ")
                    player2 = rest[:idx].strip()
                    
                    if "cùng clb" in statement_lower or "cùng câu lạc bộ" in statement_lower or "cùng đội" in statement_lower:
                        if self.check_players_same_club(player1, player2):
                            return "TRUE", 1.0
                        return "FALSE", 1.0
                    
                    if "cùng quê" in statement_lower or "cùng tỉnh" in statement_lower:
                        if self.check_players_same_province(player1, player2):
                            return "TRUE", 1.0
                        return "FALSE", 1.0
                    
                    if "cùng đội tuyển" in statement_lower or "cùng dtqg" in statement_lower:
                        if self.check_players_same_national_team(player1, player2):
                            return "TRUE", 1.0
                        return "FALSE", 1.0
        
        # Pattern 4: [Coach] huấn luyện [Team]
        if "huấn luyện" in statement_lower:
            parts = statement.split(" huấn luyện ")
            if len(parts) >= 2:
                coach = parts[0].strip()
                team = parts[1].strip().rstrip(".")
                
                if "đội tuyển" in team.lower() or "việt nam" in team.lower():
                    if self.check_coach_coached_national(coach, team):
                        return "TRUE", 1.0
                else:
                    if self.check_coach_coached_club(coach, team):
                        return "TRUE", 1.0
                return "FALSE", 1.0
        
        # Pattern 5: [Club] đóng tại/ở [Province]
        if ("đóng tại" in statement_lower or "trụ sở" in statement_lower or "đặt tại" in statement_lower):
            for sep in [" đóng tại ", " đặt tại ", " trụ sở tại ", " ở "]:
                if sep in statement.lower():
                    idx = statement.lower().find(sep)
                    club = statement[:idx].strip()
                    province = statement[idx + len(sep):].strip().rstrip(".")
                    if self.check_club_in_province(club, province):
                        return "TRUE", 1.0
                    return "FALSE", 1.0
        
        # Không nhận dạng được pattern
        logger.warning(f"Cannot parse statement: {statement}")
        return "FALSE", 0.5
    
    def answer_yes_no(self, question: str) -> Tuple[str, float]:
        """
        Trả lời câu hỏi YES/NO.
        
        Args:
            question: Câu hỏi
            
        Returns:
            ("YES" hoặc "NO", confidence)
        """
        q_lower = question.lower()
        
        # Pattern 1: [Player] có chơi cho [Club] không?
        if ("có chơi cho" in q_lower or "có thi đấu cho" in q_lower or 
            "có khoác áo" in q_lower or "đã chơi cho" in q_lower):
            
            for pattern in ["có chơi cho", "có thi đấu cho", "có khoác áo", "đã chơi cho"]:
                if pattern in q_lower:
                    idx = q_lower.find(pattern)
                    player = question[:idx].strip()
                    rest = question[idx + len(pattern):].strip()
                    club = rest.split(" không")[0].split(" chưa")[0].strip().rstrip("?")
                    
                    if self.check_player_played_for_club(player, club):
                        return "YES", 1.0
                    return "NO", 1.0
        
        # Pattern 2: [Player] có sinh ra ở [Province] không?
        if "có sinh ra" in q_lower or "quê ở" in q_lower:
            for pattern in ["có sinh ra ở", "có sinh ra tại", "quê ở", "quê tại"]:
                if pattern in q_lower:
                    idx = q_lower.find(pattern)
                    player = question[:idx].strip()
                    rest = question[idx + len(pattern):].strip()
                    province = rest.split(" không")[0].strip().rstrip("?")
                    
                    if self.check_player_born_in_province(player, province):
                        return "YES", 1.0
                    return "NO", 1.0
        
        # Pattern 3: [Player1] và [Player2] có cùng ... không?
        if " và " in question and "có cùng" in q_lower:
            parts = question.split(" và ")
            if len(parts) >= 2:
                player1 = parts[0].strip()
                rest = parts[1]
                
                idx = rest.lower().find(" có cùng ")
                if idx > 0:
                    player2 = rest[:idx].strip()
                    
                    if "cùng clb" in q_lower or "cùng câu lạc bộ" in q_lower or "cùng đội bóng" in q_lower:
                        if self.check_players_same_club(player1, player2):
                            return "YES", 1.0
                        return "NO", 1.0
                    
                    if "cùng quê" in q_lower or "cùng tỉnh" in q_lower:
                        if self.check_players_same_province(player1, player2):
                            return "YES", 1.0
                        return "NO", 1.0
                    
                    if "cùng đội tuyển" in q_lower:
                        if self.check_players_same_national_team(player1, player2):
                            return "YES", 1.0
                        return "NO", 1.0
        
        # Pattern 4: [Coach] có huấn luyện [Team] không?
        if "có huấn luyện" in q_lower:
            idx = q_lower.find("có huấn luyện")
            coach = question[:idx].strip()
            rest = question[idx + len("có huấn luyện"):].strip()
            team = rest.split(" không")[0].strip().rstrip("?")
            
            if "đội tuyển" in team.lower():
                if self.check_coach_coached_national(coach, team):
                    return "YES", 1.0
            else:
                if self.check_coach_coached_club(coach, team):
                    return "YES", 1.0
            return "NO", 1.0
        
        logger.warning(f"Cannot parse question: {question}")
        return "NO", 0.5
    
    def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float]:
        """
        Trả lời câu hỏi trắc nghiệm.
        
        Args:
            question: Câu hỏi
            choices: Danh sách các lựa chọn
            
        Returns:
            (lựa chọn đúng, confidence)
        """
        q_lower = question.lower()
        
        # Pattern 1: [Player] chơi cho CLB nào?
        if "chơi cho" in q_lower and ("clb nào" in q_lower or "câu lạc bộ nào" in q_lower or "đội nào" in q_lower):
            # Tìm tên cầu thủ
            for pattern in ["clb nào", "câu lạc bộ nào", "đội bóng nào", "đội nào"]:
                if pattern in q_lower:
                    idx = q_lower.find(pattern)
                    player = question[:idx].replace("chơi cho", "").replace("đã thi đấu cho", "").strip().rstrip("?")
                    break
            else:
                player = question.split(" chơi cho")[0].strip()
            
            clubs = self.get_player_clubs(player)
            for choice in choices:
                if any(club.lower() in choice.lower() or choice.lower() in club.lower() 
                       for club in clubs):
                    return choice, 1.0
            return choices[0], 0.3
        
        # Pattern 2: [Player] sinh ra ở đâu / quê ở đâu?
        if "sinh ra ở" in q_lower or "quê ở" in q_lower or "đến từ" in q_lower:
            for pattern in ["sinh ra ở đâu", "sinh ra ở tỉnh nào", "quê ở đâu", "quê ở tỉnh nào", "đến từ đâu"]:
                if pattern in q_lower:
                    idx = q_lower.find(pattern)
                    player = question[:idx].strip().rstrip("?")
                    break
            else:
                player = question.split(" sinh ra")[0].split(" quê")[0].strip()
            
            province = self.get_player_province(player)
            if province:
                for choice in choices:
                    if province.lower() in choice.lower() or choice.lower() in province.lower():
                        return choice, 1.0
            return choices[0], 0.3
        
        # Pattern 3: [Player] chơi ở vị trí nào?
        if "vị trí" in q_lower:
            # Tìm tên cầu thủ
            idx = q_lower.find("chơi ở vị trí")
            if idx < 0:
                idx = q_lower.find("vị trí")
            player = question[:idx].strip().rstrip("?")
            
            position = self.get_player_position(player)
            if position:
                for choice in choices:
                    if position.lower() in choice.lower() or choice.lower() in position.lower():
                        return choice, 1.0
            return choices[0], 0.3
        
        # Pattern 4: [Coach] huấn luyện đội nào?
        if "huấn luyện" in q_lower and ("đội nào" in q_lower or "clb nào" in q_lower):
            idx = q_lower.find("huấn luyện")
            coach = question[:idx].strip()
            
            teams = self.get_coach_teams(coach)
            for choice in choices:
                if any(team.lower() in choice.lower() or choice.lower() in team.lower() 
                       for team in teams):
                    return choice, 1.0
            return choices[0], 0.3
        
        # Pattern 5: Ai là cầu thủ của [Club]?
        if "ai là cầu thủ" in q_lower or "cầu thủ nào" in q_lower:
            # Tìm tên CLB
            for pattern in [" của ", " thuộc "]:
                if pattern in q_lower:
                    idx = q_lower.find(pattern)
                    club = question[idx + len(pattern):].strip().rstrip("?")
                    break
            else:
                club = ""
            
            if club:
                players = self.get_club_players(club)
                for choice in choices:
                    if any(player.lower() in choice.lower() or choice.lower() in player.lower() 
                           for player in players):
                        return choice, 1.0
            return choices[0], 0.3
        
        logger.warning(f"Cannot parse MCQ: {question}")
        return choices[0], 0.3
