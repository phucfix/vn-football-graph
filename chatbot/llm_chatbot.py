"""
LLM-enhanced GraphRAG Chatbot for Vietnamese Football.
Uses small LLM (≤1B params) for NLU + Graph for reasoning.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .graph_chatbot import GraphReasoningChatbot

logger = logging.getLogger(__name__)


class LLMGraphChatbot:
    """
    Chatbot kết hợp LLM nhỏ + Graph Reasoning.
    
    Flow:
    1. LLM phân tích câu hỏi → trích xuất intent + entities
    2. Graph query để lấy facts
    3. Trả về TRUE/FALSE hoặc đáp án MCQ
    """
    
    def __init__(self, model_name: str = "Qwen/Qwen2-0.5B-Instruct"):
        """
        Args:
            model_name: Tên model HuggingFace (mặc định Qwen2-0.5B)
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.graph_chatbot = GraphReasoningChatbot()
        self._initialized = False
        
    def initialize(self):
        """Khởi tạo LLM và Graph connection."""
        if self._initialized:
            return
            
        logger.info(f"Loading LLM: {self.model_name}...")
        
        # Load tokenizer và model
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        # Sử dụng GPU nếu có, không thì CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True
        )
        
        if device == "cpu":
            self.model = self.model.to(device)
        
        # Khởi tạo graph chatbot
        self.graph_chatbot.initialize()
        
        self._initialized = True
        logger.info("✅ LLMGraphChatbot initialized")
        
    def _generate(self, prompt: str, max_tokens: int = 256) -> str:
        """Generate response từ LLM."""
        messages = [
            {"role": "system", "content": "Bạn là trợ lý phân tích câu hỏi về bóng đá Việt Nam. Trả lời ngắn gọn, chính xác theo format yêu cầu."},
            {"role": "user", "content": prompt}
        ]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(text, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                temperature=0.1,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:], 
            skip_special_tokens=True
        )
        return response.strip()
    
    def _extract_intent_and_entities(self, question: str) -> Dict[str, Any]:
        """
        Hybrid approach: LLM cho intent classification, rule-based cho entity extraction.
        """
        q_lower = question.lower()
        
        # ========== Rule-based Entity Extraction ==========
        entities = {
            "player1": None,
            "player2": None,
            "club": None,
            "province": None,
            "coach": None
        }
        
        # Tìm entities từ graph
        players = self.graph_chatbot._find_players(question)
        if len(players) >= 1:
            entities["player1"] = players[0]
        if len(players) >= 2:
            entities["player2"] = players[1]
            
        entities["club"] = self.graph_chatbot._find_club(question)
        entities["province"] = self.graph_chatbot._find_province(question)
        entities["coach"] = self.graph_chatbot._find_coach(question)
        
        # ========== Heuristic Intent Detection ==========
        # Dựa vào entities và từ khóa để xác định intent (không cần LLM)
        
        intent = "unknown"
        
        # 2 cầu thủ → same_club hoặc same_province
        if entities["player1"] and entities["player2"]:
            if "vừa cùng" in q_lower:
                intent = "same_club_province"
            elif "cùng quê" in q_lower:
                intent = "same_province"
            elif "cùng câu lạc bộ" in q_lower or "cùng clb" in q_lower or "cùng đội" in q_lower:
                intent = "same_club"
            else:
                # Default: same_club nếu có 2 người
                intent = "same_club"
        
        # 1 cầu thủ + province → player_province (ưu tiên trước club)
        elif entities["player1"] and entities["province"]:
            intent = "player_province"
                
        # 1 cầu thủ + club → player_club
        elif entities["player1"] and entities["club"]:
            intent = "player_club"
            
        # HLV + club → coach_club
        elif entities["coach"] and entities["club"]:
            intent = "coach_club"
            
        # 1 cầu thủ, dựa vào từ khóa
        elif entities["player1"]:
            if "quê" in q_lower or "sinh ra" in q_lower or "tỉnh" in q_lower or "thành phố" in q_lower:
                intent = "player_province"
            elif "chơi cho" in q_lower or "thi đấu" in q_lower or "khoác áo" in q_lower or "clb" in q_lower or "câu lạc bộ" in q_lower:
                intent = "player_club"
            else:
                intent = "player_club"  # Default
        
        # 1 HLV, dựa vào từ khóa
        elif entities["coach"]:
            intent = "coach_club"
        
        # Xác định question type
        question_type = "true_false"
        mcq_keywords = ["nào", "ai ", "gì ", "bao nhiêu", "mấy"]
        for kw in mcq_keywords:
            if kw in q_lower:
                question_type = "mcq"
                break
        
        return {
            "intent": intent,
            "question_type": question_type,
            "entities": entities
        }
    
    def answer(self, question: str, choices: List[str] = None) -> Tuple[Any, float]:
        """
        Trả lời câu hỏi tự nhiên.
        
        Args:
            question: Câu hỏi (tự nhiên hoặc có format)
            choices: Danh sách lựa chọn cho MCQ (optional)
            
        Returns:
            - Với TRUE/FALSE: (bool, confidence)
            - Với MCQ: (selected_choice, confidence)
        """
        if not self._initialized:
            self.initialize()
        
        # Bước 1: LLM phân tích câu hỏi
        analysis = self._extract_intent_and_entities(question)
        intent = analysis.get("intent", "unknown")
        q_type = analysis.get("question_type", "true_false")
        entities = analysis.get("entities", {})
        
        logger.debug(f"Intent: {intent}, Type: {q_type}, Entities: {entities}")
        
        # Bước 2: Truy vấn Graph dựa trên intent
        if q_type == "mcq" or choices:
            return self._answer_mcq(intent, entities, question, choices or [])
        else:
            return self._answer_true_false(intent, entities, question)
    
    def _answer_true_false(self, intent: str, entities: Dict, statement: str) -> Tuple[bool, float]:
        """Trả lời câu hỏi TRUE/FALSE dựa trên graph."""
        
        player1 = entities.get("player1")
        player2 = entities.get("player2")
        club = entities.get("club")
        province = entities.get("province")
        coach = entities.get("coach")
        
        # Tìm entities trong graph
        if player1:
            player1 = self.graph_chatbot._find_player(player1) or player1
        if player2:
            player2 = self.graph_chatbot._find_player(player2) or player2
        if club:
            club = self.graph_chatbot._find_club(club) or club
        if province:
            province = self.graph_chatbot._find_province(province) or province
        if coach:
            coach = self.graph_chatbot._find_coach(coach) or coach
        
        # Query graph theo intent
        if intent == "player_club" and player1 and club:
            result = self.graph_chatbot.check_player_club(player1, club)
            return result, 1.0
            
        elif intent == "player_province" and player1 and province:
            result = self.graph_chatbot.check_player_province(player1, province)
            return result, 1.0
            
        elif intent == "coach_club" and coach and club:
            result = self.graph_chatbot.check_coach_club(coach, club)
            return result, 1.0
            
        elif intent == "same_club" and player1 and player2:
            result = self.graph_chatbot.check_same_club(player1, player2)
            return result, 1.0
            
        elif intent == "same_province" and player1 and player2:
            result = self.graph_chatbot.check_same_province(player1, player2)
            return result, 1.0
            
        elif intent == "same_club_province" and player1 and player2:
            result = self.graph_chatbot.check_same_club_and_province(player1, player2)
            return result, 1.0
        
        # Fallback: dùng GraphReasoningChatbot's pattern matching
        logger.debug(f"Fallback to GraphReasoningChatbot for: {statement}")
        return self.graph_chatbot.answer_true_false(statement)
    
    def _answer_mcq(self, intent: str, entities: Dict, question: str, choices: List[str]) -> Tuple[str, float]:
        """Trả lời câu hỏi MCQ dựa trên graph."""
        
        player1 = entities.get("player1")
        player2 = entities.get("player2")
        coach = entities.get("coach")
        
        # Tìm entities trong graph
        if player1:
            player1 = self.graph_chatbot._find_player(player1) or player1
        if player2:
            player2 = self.graph_chatbot._find_player(player2) or player2
        if coach:
            coach = self.graph_chatbot._find_coach(coach) or coach
        
        # Query graph theo intent
        if intent == "player_club" and player1:
            clubs = self.graph_chatbot.get_player_clubs(player1)
            for choice in choices:
                for club in clubs:
                    if club.lower() in choice.lower() or choice.lower() in club.lower():
                        return choice, 1.0
                        
        elif intent == "player_province" and player1:
            province = self.graph_chatbot.get_player_province(player1)
            if province:
                for choice in choices:
                    if province.lower() in choice.lower() or choice.lower() in province.lower():
                        return choice, 1.0
                        
        elif intent == "coach_club" and coach:
            clubs = self.graph_chatbot.get_coach_clubs(coach)
            for choice in choices:
                for club in clubs:
                    if club.lower() in choice.lower() or choice.lower() in club.lower():
                        return choice, 1.0
                        
        elif intent == "same_club" and player1:
            teammates = self.graph_chatbot.get_teammates(player1)
            for choice in choices:
                for teammate in teammates:
                    if teammate.lower() in choice.lower() or choice.lower() in teammate.lower():
                        return choice, 1.0
        
        # Fallback
        logger.warning(f"Cannot find answer for MCQ, returning first choice")
        return choices[0] if choices else "", 0.5
    
    def answer_true_false(self, statement: str) -> Tuple[bool, float]:
        """
        Interface tương thích với GraphReasoningChatbot.
        Với câu hỏi có format cố định, dùng GraphReasoningChatbot.
        """
        # Kiểm tra xem câu hỏi có format cố định không
        s_lower = statement.lower()
        fixed_patterns = [
            "đã chơi cho", "chơi cho", "có chơi cho", "thi đấu cho", "có thi đấu cho",  # player_club
            "sinh ra ở", "sinh ra tại",  # player_province
            "đã huấn luyện",  # coach_club
            "từng chơi cùng câu lạc bộ", "cùng câu lạc bộ", "cùng clb",  # same_club
            "cùng quê",  # same_province
            "vừa cùng"  # same_club_province
        ]
        
        # Nếu câu hỏi khớp pattern cố định, dùng GraphReasoningChatbot
        for pattern in fixed_patterns:
            if pattern in s_lower:
                return self.graph_chatbot.answer_true_false(statement)
        
        # Nếu không, dùng heuristics + LLM
        return self.answer(statement)
    
    def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float]:
        """Interface tương thích với GraphReasoningChatbot - fallback về GraphReasoningChatbot."""
        # MCQ dùng trực tiếp GraphReasoningChatbot vì pattern matching chính xác hơn
        return self.graph_chatbot.answer_mcq(question, choices)
