"""
Vietnam Football Knowledge Graph Chatbot

Main chatbot implementation with:
- Small Language Model (Qwen2-0.5B or similar < 1B params)
- GraphRAG for knowledge retrieval
- Multi-hop reasoning
"""

import logging
import torch
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import re

from .config import (
    MODEL_NAME, MODEL_MAX_LENGTH, MODEL_TEMPERATURE, MODEL_TOP_P,
    DEVICE, TORCH_DTYPE, MAX_GRAPH_CONTEXT_LENGTH
)
from .knowledge_graph import KnowledgeGraph, Entity, Relationship, get_kg
from .multi_hop_reasoning import MultiHopReasoner, ReasoningChain, QueryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Response from the chatbot."""
    answer: str
    confidence: float
    reasoning_chain: Optional[ReasoningChain]
    sources: List[str]
    model_used: str


class GraphRAGChatbot:
    """
    Knowledge Graph-based Chatbot with RAG and Multi-hop Reasoning.
    
    Architecture:
    1. Entity Recognition - Identify entities in user query
    2. Graph Retrieval - Retrieve relevant subgraph from Neo4j
    3. Multi-hop Reasoning - Traverse graph for complex queries
    4. LLM Generation - Generate natural language response
    """
    
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or MODEL_NAME
        self.device = device or DEVICE
        
        self.model = None
        self.tokenizer = None
        self.generator = None
        
        self.kg = None
        self.reasoner = None
        
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("🚀 Initializing GraphRAG Chatbot...")
        
        # Initialize Knowledge Graph
        logger.info("📊 Connecting to Knowledge Graph...")
        self.kg = KnowledgeGraph()
        if not self.kg.connect():
            logger.error("Failed to connect to Knowledge Graph")
            return False
            
        # Initialize Multi-hop Reasoner
        self.reasoner = MultiHopReasoner(self.kg)
        logger.info("🧠 Multi-hop Reasoner initialized")
        
        # Initialize Language Model
        logger.info(f"🤖 Loading Language Model: {self.model_name}")
        if not self._load_model():
            logger.warning("Failed to load LLM, will use rule-based responses")
            
        self._initialized = True
        logger.info("✅ Chatbot initialized successfully!")
        return True
        
    def _load_model(self) -> bool:
        """Load the small language model."""
        try:
            # Determine dtype
            if self.device == "cuda" and torch.cuda.is_available():
                dtype = torch.float16
                device_map = "auto"
            else:
                dtype = torch.float32
                device_map = None
                self.device = "cpu"
                
            logger.info(f"Loading model on {self.device}...")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            # Load model with efficient settings
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            # Create text generation pipeline
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map=device_map,
                torch_dtype=dtype
            )
            
            logger.info(f"✅ Model loaded: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False
            
    def chat(self, user_input: str, use_reasoning: bool = True) -> ChatResponse:
        """
        Process user input and generate response.
        
        Args:
            user_input: User's question or message
            use_reasoning: Whether to use multi-hop reasoning
            
        Returns:
            ChatResponse with answer and metadata
        """
        if not self._initialized:
            if not self.initialize():
                return ChatResponse(
                    answer="Lỗi: Chatbot chưa được khởi tạo.",
                    confidence=0.0,
                    reasoning_chain=None,
                    sources=[],
                    model_used="none"
                )
                
        # Step 1: Extract entities from user input
        entities = self._extract_entities(user_input)
        logger.info(f"Extracted entities: {entities}")
        
        # Step 2: Perform multi-hop reasoning
        reasoning_chain = None
        if use_reasoning and entities:
            reasoning_chain = self.reasoner.reason(user_input, entities)
            logger.info(f"Reasoning type: {reasoning_chain.query_type.value}")
            
        # Step 3: Build context from graph
        context = self._build_graph_context(user_input, entities, reasoning_chain)
        
        # Step 4: Generate response
        if self.generator:
            answer = self._generate_with_llm(user_input, context, reasoning_chain)
        else:
            answer = self._generate_rule_based(user_input, context, reasoning_chain)
            
        # Build response
        sources = []
        if reasoning_chain:
            sources = reasoning_chain.evidence[:5]
            
        return ChatResponse(
            answer=answer,
            confidence=reasoning_chain.confidence if reasoning_chain else 0.5,
            reasoning_chain=reasoning_chain,
            sources=sources,
            model_used=self.model_name if self.generator else "rule-based"
        )
        
    def _extract_entities(self, text: str) -> List[str]:
        """Extract entities from text using graph search."""
        entities = []
        
        # Clean text
        text = re.sub(r'[?!.,;:]', ' ', text)
        words = text.split()
        
        # Try n-grams from longest to shortest
        used_indices = set()
        
        for n in range(min(5, len(words)), 0, -1):
            for i in range(len(words) - n + 1):
                # Skip if any word already used
                if any(idx in used_indices for idx in range(i, i + n)):
                    continue
                    
                phrase = " ".join(words[i:i+n])
                
                # Skip common Vietnamese words
                skip_words = {
                    'là', 'của', 'có', 'và', 'hay', 'không', 'đã', 'từng',
                    'được', 'những', 'các', 'một', 'cho', 'với', 'trong',
                    'này', 'đó', 'như', 'thế', 'nào', 'gì', 'ai', 'bao',
                    'nhiêu', 'sao', 'vì', 'khi', 'nếu', 'nhưng', 'mà',
                    'cầu', 'thủ', 'đội', 'bóng', 'câu', 'lạc', 'bộ'
                }
                
                if phrase.lower() in skip_words:
                    continue
                    
                # Search in knowledge graph
                matches = self.kg.search_entities(phrase, limit=1)
                if matches:
                    entities.append(matches[0].name)
                    used_indices.update(range(i, i + n))
                    
        return list(dict.fromkeys(entities))  # Remove duplicates, preserve order
        
    def _build_graph_context(self, question: str, entities: List[str],
                             reasoning_chain: Optional[ReasoningChain]) -> str:
        """Build context string from graph information."""
        context_parts = []
        
        # Add reasoning evidence
        if reasoning_chain and reasoning_chain.evidence:
            context_parts.append("Thông tin từ đồ thị tri thức:")
            for ev in reasoning_chain.evidence[:10]:
                context_parts.append(f"- {ev}")
                
        # Add entity information
        for entity_name in entities[:3]:
            entity = self.kg.get_entity_by_name(entity_name)
            if entity:
                context_parts.append(f"\n{entity.to_text()}")
                
                # Add key relationships
                rels = self.kg.get_entity_relationships(entity_name)[:5]
                for rel in rels:
                    context_parts.append(f"- {rel.to_text()}")
                    
        context = "\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > MAX_GRAPH_CONTEXT_LENGTH:
            context = context[:MAX_GRAPH_CONTEXT_LENGTH] + "..."
            
        return context
        
    def _generate_with_llm(self, question: str, context: str,
                           reasoning_chain: Optional[ReasoningChain]) -> str:
        """Generate response using the language model."""
        # Build prompt
        prompt = self._build_prompt(question, context, reasoning_chain)
        
        try:
            # Generate response
            outputs = self.generator(
                prompt,
                max_new_tokens=256,
                temperature=MODEL_TEMPERATURE,
                top_p=MODEL_TOP_P,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                return_full_text=False
            )
            
            response = outputs[0]['generated_text'].strip()
            
            # Clean up response
            response = self._clean_response(response)
            
            return response
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return self._generate_rule_based(question, context, reasoning_chain)
            
    def _build_prompt(self, question: str, context: str,
                      reasoning_chain: Optional[ReasoningChain]) -> str:
        """Build prompt for the language model."""
        
        system_prompt = """Bạn là trợ lý AI chuyên về bóng đá Việt Nam. Trả lời dựa trên thông tin từ đồ thị tri thức được cung cấp.
Quy tắc:
- Chỉ trả lời dựa trên thông tin được cung cấp
- Nếu không có thông tin, hãy nói "Tôi không tìm thấy thông tin về điều này"
- Trả lời ngắn gọn, chính xác"""

        # Build context section
        context_section = f"\nThông tin từ đồ thị tri thức:\n{context}" if context else ""
        
        # Add reasoning if available
        reasoning_section = ""
        if reasoning_chain and reasoning_chain.final_answer:
            reasoning_section = f"\nKết quả suy luận: {reasoning_chain.final_answer}"
            
        # Format based on model type
        if "qwen" in self.model_name.lower():
            prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{context_section}
{reasoning_section}

Câu hỏi: {question}<|im_end|>
<|im_start|>assistant
"""
        elif "llama" in self.model_name.lower() or "tinyllama" in self.model_name.lower():
            prompt = f"""<|system|>
{system_prompt}</s>
<|user|>
{context_section}
{reasoning_section}

Câu hỏi: {question}</s>
<|assistant|>
"""
        else:
            prompt = f"""{system_prompt}

{context_section}
{reasoning_section}

Câu hỏi: {question}

Trả lời:"""
            
        return prompt
        
    def _clean_response(self, response: str) -> str:
        """Clean up the generated response."""
        # Remove special tokens
        response = re.sub(r'<\|.*?\|>', '', response)
        response = re.sub(r'</s>', '', response)
        
        # Remove repetitions
        sentences = response.split('.')
        seen = set()
        unique_sentences = []
        for s in sentences:
            s = s.strip()
            if s and s not in seen:
                seen.add(s)
                unique_sentences.append(s)
                
        response = '. '.join(unique_sentences)
        if response and not response.endswith('.'):
            response += '.'
            
        return response.strip()
        
    def _generate_rule_based(self, question: str, context: str,
                             reasoning_chain: Optional[ReasoningChain]) -> str:
        """Generate response using rules (fallback when no LLM)."""
        if reasoning_chain:
            return reasoning_chain.final_answer
            
        if context:
            return f"Dựa trên đồ thị tri thức:\n{context}"
            
        return "Tôi không tìm thấy thông tin liên quan trong đồ thị tri thức."
        
    def answer_yes_no(self, question: str) -> Tuple[str, float, str]:
        """
        Answer a yes/no question.
        
        Returns:
            Tuple of (answer: "Đúng"/"Sai", confidence, explanation)
        """
        entities = self._extract_entities(question)
        
        if self.reasoner:
            is_true, confidence, explanation = self.reasoner.answer_yes_no(question, entities)
            answer = "Đúng" if is_true else "Sai"
            return answer, confidence, explanation
            
        return "Không rõ", 0.0, "Không thể xác định"
        
    def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float, str]:
        """
        Answer a multiple choice question.
        
        Returns:
            Tuple of (selected_choice, confidence, explanation)
        """
        entities = self._extract_entities(question)
        
        # Evaluate each choice
        best_choice = None
        best_confidence = 0.0
        best_explanation = ""
        
        for choice in choices:
            # Combine question with choice
            full_question = f"{question} {choice}"
            choice_entities = entities + self._extract_entities(choice)
            
            # Reason about this choice
            chain = self.reasoner.reason(full_question, choice_entities)
            
            if chain.confidence > best_confidence:
                best_confidence = chain.confidence
                best_choice = choice
                best_explanation = chain.final_answer
                
        return best_choice or choices[0], best_confidence, best_explanation
        
    def close(self):
        """Clean up resources."""
        if self.kg:
            self.kg.close()
        if self.model:
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            

class SimpleChatbot:
    """
    Simplified chatbot without LLM - uses only graph reasoning.
    Faster and lighter, good for evaluation.
    """
    
    def __init__(self):
        self.kg = None
        self.reasoner = None
        
    def initialize(self) -> bool:
        """Initialize the chatbot."""
        self.kg = KnowledgeGraph()
        if not self.kg.connect():
            return False
        self.reasoner = MultiHopReasoner(self.kg)
        return True
        
    def chat(self, question: str) -> str:
        """Answer a question using graph reasoning only."""
        question_lower = question.lower()
        
        # Check if this is a question about national team
        if self._is_national_team_question(question_lower):
            return self._answer_national_team_question(question)
        
        # Check if this is a birthplace question
        if self._is_birthplace_question(question_lower):
            return self._answer_birthplace_question(question)
        
        # Check if this is a Yes/No question about playing for a club
        if self._is_played_for_question(question_lower):
            return self._answer_played_for_question(question)
        
        # Check if this is a general Yes/No question
        if self._is_yes_no_question(question_lower):
            answer, confidence = self.answer_yes_no(question)
            return answer
        
        # Default: use general reasoning
        entities = self._extract_entities(question)
        chain = self.reasoner.reason(question, entities)
        return chain.final_answer
    
    def _is_national_team_question(self, question_lower: str) -> bool:
        """Check if question asks about national team."""
        patterns = ['đội tuyển', 'quốc gia', 'tuyển việt nam', 'tuyển quốc gia', 'khoác áo đội tuyển']
        return any(p in question_lower for p in patterns)
    
    def _is_birthplace_question(self, question_lower: str) -> bool:
        """Check if question asks about birthplace."""
        patterns = ['sinh ra', 'sinh ở', 'quê ở', 'quê', 'đến từ', 'nơi sinh', 'ở đâu']
        return any(p in question_lower for p in patterns)
    
    def _answer_national_team_question(self, question: str) -> str:
        """Answer question about national team."""
        player = self._extract_player_from_question(question)
        
        if not player:
            entities = self._extract_entities(question)
            for entity in entities:
                result = self.kg.execute_cypher(
                    "MATCH (p:Player {name: $name}) RETURN p LIMIT 1",
                    {"name": entity}
                )
                if result:
                    player = entity
                    break
        
        if not player:
            return "Không tìm thấy cầu thủ trong câu hỏi."
        
        # Check national team
        result = self.kg.execute_cypher("""
            MATCH (p:Player {name: $name})-[:PLAYED_FOR_NATIONAL]->(n:NationalTeam)
            RETURN n.name as team
        """, {"name": player})
        
        if result:
            teams = [r['team'] for r in result]
            teams_str = ", ".join(teams)
            return f"Có, {player} từng khoác áo đội tuyển: {teams_str}."
        else:
            return f"Không, {player} chưa từng khoác áo đội tuyển quốc gia."
    
    def _answer_birthplace_question(self, question: str) -> str:
        """Answer question about birthplace."""
        player = self._extract_player_from_question(question)
        
        if not player:
            entities = self._extract_entities(question)
            for entity in entities:
                result = self.kg.execute_cypher(
                    "MATCH (p:Player {name: $name}) RETURN p LIMIT 1",
                    {"name": entity}
                )
                if result:
                    player = entity
                    break
        
        if not player:
            return "Không tìm thấy cầu thủ trong câu hỏi."
        
        # Get birthplace
        result = self.kg.execute_cypher("""
            MATCH (p:Player {name: $name})-[:BORN_IN]->(pr:Province)
            RETURN pr.name as province
        """, {"name": player})
        
        if result:
            province = result[0]['province']
            return f"{player} sinh ra tại {province}."
        else:
            return f"Không tìm thấy thông tin nơi sinh của {player}."
    
    def _is_played_for_question(self, question_lower: str) -> bool:
        """Check if question asks about player playing for a club."""
        # NOT a same-club question
        if 'cùng câu lạc bộ' in question_lower or 'chơi cùng' in question_lower:
            return False
        patterns = [
            'chơi cho', 'thi đấu cho', 'khoác áo', 'từng chơi', 
            'đá cho', 'thuộc', 'ở clb', 'ở câu lạc bộ'
        ]
        return any(p in question_lower for p in patterns)
    
    def _is_yes_no_question(self, question_lower: str) -> bool:
        """Check if this is a Yes/No question."""
        patterns = [
            'có phải', 'có phải là', 'đúng không', 'phải không',
            'có từng', 'đã từng', 'không?', 'chưa?', 'à?'
        ]
        return any(p in question_lower for p in patterns)
    
    def _answer_played_for_question(self, question: str) -> str:
        """Answer a specific question about player playing for club."""
        question_lower = question.lower()
        
        # First, try to identify club from common abbreviations and names
        club = self._extract_club_from_question(question_lower)
        
        # Then find player - prioritize finding player name in question
        player = self._extract_player_from_question(question)
        
        if not player:
            entities = self._extract_entities(question)
            # Find player from entities
            for entity in entities:
                result = self.kg.execute_cypher(
                    "MATCH (p:Player {name: $name}) RETURN p LIMIT 1",
                    {"name": entity}
                )
                if result:
                    player = entity
                    break
        
        if not player:
            return f"Không tìm thấy cầu thủ trong câu hỏi."
        
        if not club:
            return f"Không tìm thấy câu lạc bộ trong câu hỏi. Bạn hỏi về CLB nào?"
        
        # Check if player played for club
        played = self._check_played_for(player, club)
        
        if played:
            return f"Có, {player} từng chơi cho {club}."
        else:
            # Get clubs the player actually played for
            clubs = self._get_player_clubs(player)
            if clubs:
                clubs_str = ", ".join(clubs[:5])
                return f"Không, {player} không từng chơi cho {club}. {player} từng chơi cho: {clubs_str}."
            return f"Không, {player} không từng chơi cho {club}."
    
    def _extract_club_from_question(self, question_lower: str) -> Optional[str]:
        """Extract club name from question, handling abbreviations."""
        # Dictionary of common club names and abbreviations
        club_patterns = {
            'công an hà nội': 'Công an Hà Nội',
            'cahn': 'Công an Hà Nội',
            'slna': 'Câu lạc bộ bóng đá Sông Lam Nghệ An',
            'sông lam nghệ an': 'Câu lạc bộ bóng đá Sông Lam Nghệ An',
            'sông lam': 'Câu lạc bộ bóng đá Sông Lam Nghệ An',
            'hagl': 'Câu lạc bộ bóng đá Hoàng Anh Gia Lai',
            'hoàng anh gia lai': 'Câu lạc bộ bóng đá Hoàng Anh Gia Lai',
            'gia lai': 'Câu lạc bộ bóng đá Hoàng Anh Gia Lai',
            'hà nội fc': 'Hà Nội',
            'clb hà nội': 'Hà Nội',
            'viettel': 'Câu lạc bộ bóng đá Thể Công – Viettel',
            'thể công': 'Câu lạc bộ bóng đá Thể Công – Viettel',
            'bình dương': 'Câu lạc bộ bóng đá Bình Dương',
            'đà nẵng': 'Câu lạc bộ bóng đá SHB Đà Nẵng',
            'shb đà nẵng': 'Câu lạc bộ bóng đá SHB Đà Nẵng',
            'hải phòng': 'Câu lạc bộ bóng đá Hải Phòng',
            'thanh hóa': 'Câu lạc bộ bóng đá Đông Á Thanh Hóa',
            'nam định': 'Câu lạc bộ bóng đá Thép Xanh Nam Định',
            'quảng nam': 'Câu lạc bộ bóng đá Quảng Nam',
            'tp.hcm': 'Câu lạc bộ bóng đá Công an Thành phố Hồ Chí Minh',
            'tp hcm': 'Câu lạc bộ bóng đá Công an Thành phố Hồ Chí Minh',
        }
        
        # Check for abbreviations first (longer patterns first)
        for pattern, club_name in sorted(club_patterns.items(), key=lambda x: -len(x[0])):
            if pattern in question_lower:
                return club_name
        
        # Special case: "Hà Nội" without "Công an"
        if 'hà nội' in question_lower and 'công an' not in question_lower:
            return 'Hà Nội'
        
        return None
    
    def _extract_player_from_question(self, question: str) -> Optional[str]:
        """Extract player name from question, handling common short names."""
        question_lower = question.lower()
        
        # Common player nicknames/short names
        player_patterns = {
            'công phượng': 'Nguyễn Công Phượng',
            'quang hải': 'Nguyễn Quang Hải',
            'văn toàn': 'Nguyễn Văn Toàn',
            'văn hậu': 'Đoàn Văn Hậu',
            'tiến linh': 'Nguyễn Tiến Linh',
            'đức chinh': 'Hà Đức Chinh',
            'hùng dũng': 'Đỗ Hùng Dũng',
            'xuân trường': 'Lương Xuân Trường',
            'tuấn anh': 'Nguyễn Tuấn Anh',
            'hoàng đức': 'Nguyễn Hoàng Đức',
            'văn lâm': 'Đặng Văn Lâm',
            'văn quyết': 'Nguyễn Văn Quyết',
            'anh đức': 'Nguyễn Anh Đức',
            'minh vương': 'Trần Minh Vương',
            'huỳnh như': 'Cù Thị Huỳnh Như',
        }
        
        for pattern, full_name in player_patterns.items():
            if pattern in question_lower:
                return full_name
        
        return None
    
    def _get_player_clubs(self, player: str) -> List[str]:
        """Get all clubs a player has played for."""
        result = self.kg.execute_cypher("""
            MATCH (p:Player {name: $name})-[:PLAYED_FOR]->(c:Club)
            RETURN c.name as club
        """, {"name": player})
        return [r['club'] for r in result] if result else []
        
    def _extract_entities(self, text: str) -> List[str]:
        """Extract entities from text."""
        entities = []
        text = re.sub(r'[?!.,;:]', ' ', text)
        words = text.split()
        
        for n in range(min(5, len(words)), 0, -1):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i+n])
                matches = self.kg.search_entities(phrase, limit=1)
                if matches:
                    entities.append(matches[0].name)
                    
        return list(dict.fromkeys(entities))
    
    def _check_played_for(self, player: str, club: str) -> bool:
        """Check if player played for specific club.
        
        Uses strict matching to avoid false positives.
        """
        rels = self.kg.get_entity_relationships(player)
        club_lower = club.lower()
        
        # Extract key identifier from club name (usually location name)
        club_key_words = []
        location_keywords = ['hà nội', 'sài gòn', 'đà nẵng', 'hải phòng', 'thanh hóa', 
                           'nghệ an', 'quảng nam', 'quảng ninh', 'ninh bình', 'bình dương',
                           'long an', 'cần thơ', 'vĩnh long', 'gia lai', 'huế', 'khánh hòa',
                           'bình định', 'tây ninh', 'đồng nai', 'hồ chí minh', 'nam định',
                           'thái bình', 'đồng tháp', 'an giang', 'bình phước', 'lâm đồng']
        
        for kw in location_keywords:
            if kw in club_lower:
                club_key_words.append(kw)
        
        for rel in rels:
            if rel.relation_type in ["PLAYED_FOR", "PLAYED_FOR_NATIONAL"]:
                target_lower = rel.target.name.lower()
                
                # Exact match
                if club_lower == target_lower:
                    return True
                
                # One fully contains the other (strict substring)
                if club_lower in target_lower or target_lower in club_lower:
                    # Additional check: key location must match
                    if club_key_words:
                        for kw in club_key_words:
                            if kw in target_lower:
                                return True
                    else:
                        return True
                
        return False
    
    def _check_born_in(self, player: str, place: str) -> bool:
        """Check if player was born in specific place."""
        rels = self.kg.get_entity_relationships(player)
        place_lower = place.lower()
        for rel in rels:
            if rel.relation_type in ["BORN_IN", "FROM_PROVINCE"]:
                target_lower = rel.target.name.lower()
                if place_lower in target_lower or target_lower in place_lower:
                    return True
        return False
    
    def _check_national_team(self, player: str) -> bool:
        """Check if player played for national team."""
        rels = self.kg.get_entity_relationships(player)
        for rel in rels:
            if rel.relation_type == "PLAYED_FOR_NATIONAL":
                return True
        return False
        
    def answer_yes_no(self, question: str) -> Tuple[str, float]:
        """Answer yes/no question with multi-hop reasoning."""
        entities = self._extract_entities(question)
        question_lower = question.lower()
        
        # Pattern 1: "X và Y từng chơi cùng câu lạc bộ" (2-hop)
        if "cùng câu lạc bộ" in question_lower or "chơi cùng" in question_lower:
            if len(entities) >= 2:
                same_club, club = self.kg.check_same_club(entities[0], entities[1])
                if same_club:
                    return "Có", 0.95
                same_club, club = self.kg.check_same_club(entities[1], entities[0])
                if same_club:
                    return "Có", 0.95
                return "Không", 0.85
        
        # Pattern 2: "X và Y là đồng đội" (1-hop or 2-hop)
        if "đồng đội" in question_lower:
            if len(entities) >= 2:
                is_teammate, info = self.kg.check_teammates(entities[0], entities[1])
                if is_teammate:
                    return "Có", 0.95
                is_teammate, info = self.kg.check_teammates(entities[1], entities[0])
                if is_teammate:
                    return "Có", 0.95
                return "Không", 0.85
        
        # Pattern 3: "X từng chơi cho CLB ở tỉnh có cầu thủ Y" (3-hop)
        if "ở tỉnh có cầu thủ" in question_lower or "tỉnh có cầu thủ" in question_lower:
            if len(entities) >= 2:
                played_in_province, club, province = self.kg.check_played_in_province_of_player(
                    entities[0], entities[1]
                )
                if played_in_province:
                    return "Có", 0.95
                return "Không", 0.85
        
        # Pattern 4: "X cùng quê với Y" (2-hop via province)
        if "cùng quê" in question_lower or "cùng tỉnh" in question_lower:
            if len(entities) >= 2:
                same_province, province = self.kg.check_same_province_via_club(entities[0], entities[1])
                if same_province:
                    return "Có", 0.95
                return "Không", 0.85
        
        # Pattern 5: "X từng chơi cho Y" (1-hop) - SPECIFIC CHECK
        if ("từng chơi cho" in question_lower or "chơi cho" in question_lower) and len(entities) >= 2:
            player = entities[0]
            club = entities[1]
            if self._check_played_for(player, club):
                return "Có", 0.95
            # Try reverse (in case entity order is wrong)
            if self._check_played_for(club, player):
                return "Có", 0.95
            return "Không", 0.90
        
        # Pattern 6: "X sinh ra tại Y" (1-hop) - SPECIFIC CHECK
        if ("sinh ra" in question_lower or "sinh tại" in question_lower or "quê" in question_lower) and len(entities) >= 2:
            player = entities[0]
            place = entities[1]
            if self._check_born_in(player, place):
                return "Có", 0.95
            return "Không", 0.90
        
        # Pattern 7: "X có từng khoác áo đội tuyển quốc gia" (1-hop)
        if "đội tuyển quốc gia" in question_lower or "khoác áo" in question_lower:
            if entities:
                player = entities[0]
                if self._check_national_team(player):
                    return "Có", 0.95
                return "Không", 0.90
        
        # Fallback: Only answer "Có" if we find EXACT matching relationship
        if entities and len(entities) >= 2:
            entity1 = entities[0]
            entity2 = entities[1]
            
            # Get relationships and check for direct connection with matching type
            rels = self.kg.get_entity_relationships(entity1)
            entity2_lower = entity2.lower()
            
            for rel in rels:
                target_lower = rel.target.name.lower()
                # Check if entity2 matches target
                if entity2_lower in target_lower or target_lower in entity2_lower:
                    return "Có", 0.9
            
            # Check reverse direction
            rels2 = self.kg.get_entity_relationships(entity2)
            entity1_lower = entity1.lower()
            
            for rel in rels2:
                target_lower = rel.target.name.lower()
                if entity1_lower in target_lower or target_lower in entity1_lower:
                    return "Có", 0.9
                    
            # No direct relationship found
            return "Không", 0.7
        
        # Single entity - check if question asks about specific property
        if entities:
            return "Không", 0.6
        
        return "Không", 0.6
        
    def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float, str]:
        """Answer multiple choice question."""
        entities = self._extract_entities(question)
        
        if not entities:
            return choices[0] if choices else "", 0.25, "Không tìm thấy thực thể"
            
        entity = entities[0]
        rels = self.kg.get_entity_relationships(entity)
        
        # Score each choice
        best_choice = choices[0] if choices else ""
        best_score = 0.0
        explanation = ""
        
        for choice in choices:
            score = 0.0
            
            # Check if choice matches any relationship target
            for rel in rels:
                if choice.lower() in rel.target.name.lower() or rel.target.name.lower() in choice.lower():
                    score = 0.9
                    explanation = rel.to_text()
                    break
                    
            # Check partial match
            if score == 0:
                choice_words = set(choice.lower().split())
                for rel in rels:
                    target_words = set(rel.target.name.lower().split())
                    overlap = len(choice_words & target_words)
                    if overlap > 0:
                        score = 0.5 * (overlap / max(len(choice_words), len(target_words)))
                        
            if score > best_score:
                best_score = score
                best_choice = choice
                
        return best_choice, best_score, explanation
        
    def close(self):
        """Clean up."""
        if self.kg:
            self.kg.close()


class HybridChatbot:
    """
    Hybrid Chatbot combining:
    1. Graph Reasoning (SimpleChatbot) - For accurate answers from Knowledge Graph
    2. Small LLM (Qwen2-0.5B) - For natural language formatting
    
    This approach satisfies:
    - Requirement (1): Uses LLM ≤ 1B params
    - Requirement (2): Uses Knowledge Graph + GraphRAG
    - Requirement (3): Multi-hop reasoning via graph traversal
    
    The key insight: LLM is used to FORMAT the answer, not to FIND the answer.
    Graph reasoning finds the accurate answer, LLM makes it sound natural.
    """
    
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or MODEL_NAME
        self.device = device or DEVICE
        
        # LLM components
        self.model = None
        self.tokenizer = None
        self.generator = None
        
        # Graph reasoning component (SimpleChatbot)
        self.graph_reasoner = SimpleChatbot()
        
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("🚀 Initializing Hybrid Chatbot...")
        
        # Initialize graph reasoner first (critical component)
        logger.info("📊 Initializing Graph Reasoner...")
        if not self.graph_reasoner.initialize():
            logger.error("Failed to initialize graph reasoner")
            return False
        logger.info("✅ Graph Reasoner ready")
        
        # Initialize LLM (optional, for formatting)
        logger.info(f"🤖 Loading LLM for formatting: {self.model_name}")
        self._load_model()  # Don't fail if LLM doesn't load
        
        self._initialized = True
        logger.info("✅ Hybrid Chatbot initialized!")
        return True
        
    def _load_model(self) -> bool:
        """Load the small language model for formatting."""
        try:
            if self.device == "cuda" and torch.cuda.is_available():
                dtype = torch.float16
                device_map = "auto"
            else:
                dtype = torch.float32
                device_map = None
                self.device = "cpu"
                
            logger.info(f"Loading model on {self.device}...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map=device_map,
                torch_dtype=dtype
            )
            
            logger.info(f"✅ LLM loaded: {self.model_name}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load LLM: {e}")
            logger.info("Will use graph reasoning without LLM formatting")
            return False
    
    def answer_yes_no(self, question: str) -> Tuple[str, float, str]:
        """
        Answer yes/no question using Graph Reasoning.
        LLM is NOT used for finding the answer - only graph traversal.
        
        Returns:
            Tuple of (answer, confidence, explanation)
        """
        # Use graph reasoning to get the accurate answer
        answer, confidence = self.graph_reasoner.answer_yes_no(question)
        
        # Generate explanation based on graph data
        entities = self.graph_reasoner._extract_entities(question)
        explanation = f"Dựa trên đồ thị tri thức với các thực thể: {', '.join(entities[:3]) if entities else 'không xác định'}"
        
        return answer, confidence, explanation
    
    def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float, str]:
        """
        Answer MCQ using Graph Reasoning.
        
        Returns:
            Tuple of (selected_choice, confidence, explanation)
        """
        return self.graph_reasoner.answer_mcq(question, choices)
    
    def chat(self, question: str) -> str:
        """
        Answer a question using Hybrid approach:
        1. Graph Reasoning finds the answer
        2. (Optional) LLM formats the response
        """
        # Step 1: Get answer from graph reasoning
        graph_answer = self.graph_reasoner.chat(question)
        
        # Step 2: If LLM is available, format the response
        if self.generator and len(graph_answer) > 10:
            try:
                formatted = self._format_with_llm(question, graph_answer)
                return formatted
            except Exception as e:
                logger.warning(f"LLM formatting failed: {e}")
                return graph_answer
        
        return graph_answer
    
    def _format_with_llm(self, question: str, graph_answer: str) -> str:
        """Use LLM to format the graph answer more naturally."""
        prompt = f"""<|im_start|>system
Bạn là trợ lý AI về bóng đá Việt Nam. Định dạng lại câu trả lời cho tự nhiên hơn.
Giữ nguyên thông tin chính xác, chỉ làm cho câu trả lời tự nhiên hơn.<|im_end|>
<|im_start|>user
Câu hỏi: {question}
Thông tin từ đồ thị: {graph_answer}
Hãy trả lời ngắn gọn, tự nhiên:<|im_end|>
<|im_start|>assistant
"""
        
        try:
            outputs = self.generator(
                prompt,
                max_new_tokens=100,
                temperature=0.3,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                return_full_text=False
            )
            
            response = outputs[0]['generated_text'].strip()
            # Clean up
            response = re.sub(r'<\|.*?\|>', '', response)
            
            # If LLM response is too short or weird, return original
            if len(response) < 5 or response.lower() == graph_answer.lower():
                return graph_answer
                
            return response
            
        except Exception:
            return graph_answer
    
    @property
    def kg(self):
        """Access to knowledge graph."""
        return self.graph_reasoner.kg
    
    def close(self):
        """Clean up resources."""
        if self.graph_reasoner:
            self.graph_reasoner.close()
        if self.model:
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# Factory function
def create_chatbot(use_llm: bool = True, hybrid: bool = False) -> Any:
    """Create and initialize a chatbot instance.
    
    Args:
        use_llm: If True and hybrid=False, use GraphRAGChatbot (pure LLM)
        hybrid: If True, use HybridChatbot (Graph + LLM formatting)
    """
    if hybrid:
        chatbot = HybridChatbot()
    elif use_llm:
        chatbot = GraphRAGChatbot()
    else:
        chatbot = SimpleChatbot()
        
    chatbot.initialize()
    return chatbot
