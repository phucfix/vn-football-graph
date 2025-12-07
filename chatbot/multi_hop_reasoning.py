"""
Multi-hop Reasoning Engine for Knowledge Graph

This module implements multi-hop reasoning over the knowledge graph,
allowing the chatbot to answer complex questions that require
traversing multiple relationships.

Supports:
- Single-hop queries (direct relationships)
- Multi-hop queries (2-3 hop paths)
- Path-based reasoning
- Aggregation queries
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .knowledge_graph import KnowledgeGraph, Entity, Relationship, Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries supported."""
    ENTITY_LOOKUP = "entity_lookup"           # What is X?
    RELATIONSHIP = "relationship"              # What is the relationship between X and Y?
    ONE_HOP = "one_hop"                        # Who played for X?
    TWO_HOP = "two_hop"                        # Who are teammates of players from X?
    THREE_HOP = "three_hop"                    # Complex multi-hop queries
    AGGREGATION = "aggregation"               # How many players from X?
    PATH_FINDING = "path_finding"              # How are X and Y connected?
    COMPARISON = "comparison"                  # Compare X and Y


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_number: int
    query: str
    result: Any
    explanation: str
    entities_involved: List[Entity]
    relationships_found: List[Relationship]


@dataclass
class ReasoningChain:
    """Complete reasoning chain for a query."""
    question: str
    query_type: QueryType
    steps: List[ReasoningStep]
    final_answer: str
    confidence: float
    evidence: List[str]
    
    def to_text(self) -> str:
        """Convert reasoning chain to readable text."""
        lines = [f"Câu hỏi: {self.question}\n"]
        lines.append(f"Loại truy vấn: {self.query_type.value}\n")
        lines.append("Quá trình suy luận:\n")
        
        for step in self.steps:
            lines.append(f"  Bước {step.step_number}: {step.explanation}")
            
        lines.append(f"\nKết luận: {self.final_answer}")
        lines.append(f"Độ tin cậy: {self.confidence:.2%}")
        
        if self.evidence:
            lines.append("\nBằng chứng:")
            for ev in self.evidence[:5]:
                lines.append(f"  - {ev}")
                
        return "\n".join(lines)


class MultiHopReasoner:
    """
    Multi-hop reasoning engine over the knowledge graph.
    
    Implements chain-of-thought reasoning for complex queries.
    """
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.kg = knowledge_graph
        
        # Relationship mappings for Vietnamese questions
        self.relation_keywords = {
            "chơi cho": ["PLAYED_FOR", "PLAYED_FOR_NATIONAL"],
            "đồng đội": ["TEAMMATE", "NATIONAL_TEAMMATE"],
            "huấn luyện": ["COACHED", "COACHED_NATIONAL"],
            "sinh ra": ["BORN_IN"],
            "quê": ["FROM_PROVINCE", "BORN_IN"],
            "sân nhà": ["HOME_STADIUM"],
            "giải đấu": ["COMPETED_IN", "COMPETES_IN"],
            "vị trí": ["HAS_POSITION"],
            "cùng câu lạc bộ": ["PLAYED_SAME_CLUBS"],
            "cùng quê": ["SAME_PROVINCE"],
        }
        
    def reason(self, question: str, entities: List[str] = None) -> ReasoningChain:
        """
        Main reasoning method. Analyzes question and performs multi-hop reasoning.
        
        Args:
            question: Natural language question
            entities: Pre-extracted entities (optional)
            
        Returns:
            ReasoningChain with full reasoning trace
        """
        # Step 1: Analyze question type
        query_type = self._classify_query(question)
        logger.info(f"Query type: {query_type.value}")
        
        # Step 2: Extract entities if not provided
        if not entities:
            entities = self._extract_entities(question)
        logger.info(f"Entities: {entities}")
        
        # Step 3: Execute appropriate reasoning strategy
        if query_type == QueryType.ENTITY_LOOKUP:
            return self._reason_entity_lookup(question, entities)
        elif query_type == QueryType.RELATIONSHIP:
            return self._reason_relationship(question, entities)
        elif query_type == QueryType.ONE_HOP:
            return self._reason_one_hop(question, entities)
        elif query_type == QueryType.TWO_HOP:
            return self._reason_two_hop(question, entities)
        elif query_type == QueryType.THREE_HOP:
            return self._reason_three_hop(question, entities)
        elif query_type == QueryType.PATH_FINDING:
            return self._reason_path_finding(question, entities)
        elif query_type == QueryType.AGGREGATION:
            return self._reason_aggregation(question, entities)
        else:
            return self._reason_general(question, entities)
            
    def _classify_query(self, question: str) -> QueryType:
        """Classify the type of query based on question patterns."""
        q = question.lower()
        
        # Path finding patterns
        if any(p in q for p in ["mối quan hệ", "liên quan", "kết nối", "con đường"]):
            return QueryType.PATH_FINDING
            
        # Aggregation patterns
        if any(p in q for p in ["bao nhiêu", "có mấy", "đếm", "số lượng", "tổng"]):
            return QueryType.AGGREGATION
            
        # Comparison patterns
        if any(p in q for p in ["so sánh", "khác nhau", "giống nhau"]):
            return QueryType.COMPARISON
            
        # Multi-hop indicators
        hop_indicators = [
            ("đồng đội của", "từng chơi"),  # teammates of players who played for
            ("huấn luyện viên", "đội"),     # coaches of teams
            ("cầu thủ", "quê"),              # players from province
        ]
        
        hop_count = 0
        for indicator in hop_indicators:
            if all(i in q for i in indicator):
                hop_count += 1
                
        # Count relationship keywords
        for keyword in self.relation_keywords.keys():
            if keyword in q:
                hop_count += 1
                
        if hop_count >= 3:
            return QueryType.THREE_HOP
        elif hop_count >= 2:
            return QueryType.TWO_HOP
        elif hop_count >= 1:
            return QueryType.ONE_HOP
            
        # Check if it's asking about relationship between two entities
        if " và " in q and any(p in q for p in ["quan hệ", "liên quan"]):
            return QueryType.RELATIONSHIP
            
        return QueryType.ENTITY_LOOKUP
        
    def _extract_entities(self, question: str) -> List[str]:
        """Extract entity names from question using graph search."""
        # Simple approach: search for matches in the graph
        words = question.split()
        entities = []
        
        # Try different n-grams
        for n in range(4, 0, -1):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i+n])
                # Skip common words
                if phrase.lower() in ["là", "của", "có", "và", "hay", "không", "đã", "từng"]:
                    continue
                    
                matches = self.kg.search_entities(phrase, limit=1)
                if matches:
                    entities.append(matches[0].name)
                    
        return list(set(entities))
        
    def _reason_entity_lookup(self, question: str, entities: List[str]) -> ReasoningChain:
        """Reason about entity lookup queries."""
        steps = []
        evidence = []
        
        if not entities:
            return ReasoningChain(
                question=question,
                query_type=QueryType.ENTITY_LOOKUP,
                steps=[],
                final_answer="Không tìm thấy thực thể nào trong câu hỏi.",
                confidence=0.0,
                evidence=[]
            )
            
        # Get entity information
        entity_name = entities[0]
        entity = self.kg.get_entity_by_name(entity_name)
        
        if not entity:
            return ReasoningChain(
                question=question,
                query_type=QueryType.ENTITY_LOOKUP,
                steps=[],
                final_answer=f"Không tìm thấy thông tin về '{entity_name}'.",
                confidence=0.0,
                evidence=[]
            )
            
        # Step 1: Get entity info
        step1 = ReasoningStep(
            step_number=1,
            query=f"Tìm thông tin về {entity_name}",
            result=entity,
            explanation=f"Tìm thấy {entity.label}: {entity.name}",
            entities_involved=[entity],
            relationships_found=[]
        )
        steps.append(step1)
        evidence.append(entity.to_text())
        
        # Step 2: Get relationships
        relationships = self.kg.get_entity_relationships(entity_name)
        step2 = ReasoningStep(
            step_number=2,
            query=f"Lấy các mối quan hệ của {entity_name}",
            result=relationships,
            explanation=f"Tìm thấy {len(relationships)} mối quan hệ",
            entities_involved=[entity],
            relationships_found=relationships[:10]
        )
        steps.append(step2)
        
        for rel in relationships[:5]:
            evidence.append(rel.to_text())
            
        # Compose answer
        answer_parts = [f"{entity.name} là một {entity.label}."]
        
        if entity.properties:
            props = [f"{k}: {v}" for k, v in entity.properties.items() if v][:3]
            if props:
                answer_parts.append(f"Thông tin: {', '.join(props)}.")
                
        if relationships:
            rel_summary = []
            for rel in relationships[:3]:
                rel_summary.append(rel.to_text())
            answer_parts.append(f"Các mối quan hệ: {'; '.join(rel_summary)}.")
            
        return ReasoningChain(
            question=question,
            query_type=QueryType.ENTITY_LOOKUP,
            steps=steps,
            final_answer=" ".join(answer_parts),
            confidence=0.9 if relationships else 0.7,
            evidence=evidence
        )
        
    def _reason_one_hop(self, question: str, entities: List[str]) -> ReasoningChain:
        """Reason about one-hop queries (direct relationships)."""
        steps = []
        evidence = []
        
        if not entities:
            return self._no_entity_response(question, QueryType.ONE_HOP)
            
        entity_name = entities[0]
        
        # Step 1: Find entity
        entity = self.kg.get_entity_by_name(entity_name)
        if not entity:
            return self._entity_not_found_response(question, entity_name, QueryType.ONE_HOP)
            
        step1 = ReasoningStep(
            step_number=1,
            query=f"Xác định thực thể {entity_name}",
            result=entity,
            explanation=f"Tìm thấy {entity.label}: {entity.name}",
            entities_involved=[entity],
            relationships_found=[]
        )
        steps.append(step1)
        
        # Step 2: Determine relationship type from question
        rel_types = self._get_relationship_types_from_question(question)
        
        # Step 3: Get relationships
        relationships = self.kg.get_entity_relationships(
            entity_name, 
            rel_types=rel_types if rel_types else None
        )
        
        step2 = ReasoningStep(
            step_number=2,
            query=f"Tìm các mối quan hệ {rel_types or 'tất cả'} của {entity_name}",
            result=relationships,
            explanation=f"Tìm thấy {len(relationships)} mối quan hệ phù hợp",
            entities_involved=[entity],
            relationships_found=relationships[:10]
        )
        steps.append(step2)
        
        for rel in relationships[:10]:
            evidence.append(rel.to_text())
            
        # Compose answer
        if relationships:
            unique_targets = list(set(rel.target.name for rel in relationships[:20]))
            answer = f"Dựa trên đồ thị tri thức, {entity_name} có quan hệ với: {', '.join(unique_targets[:10])}"
            if len(unique_targets) > 10:
                answer += f" và {len(unique_targets) - 10} thực thể khác."
            confidence = 0.9
        else:
            answer = f"Không tìm thấy mối quan hệ phù hợp cho {entity_name}."
            confidence = 0.3
            
        return ReasoningChain(
            question=question,
            query_type=QueryType.ONE_HOP,
            steps=steps,
            final_answer=answer,
            confidence=confidence,
            evidence=evidence
        )
        
    def _reason_two_hop(self, question: str, entities: List[str]) -> ReasoningChain:
        """Reason about two-hop queries."""
        steps = []
        evidence = []
        
        if not entities:
            return self._no_entity_response(question, QueryType.TWO_HOP)
            
        entity_name = entities[0]
        
        # Step 1: Find starting entity
        entity = self.kg.get_entity_by_name(entity_name)
        if not entity:
            return self._entity_not_found_response(question, entity_name, QueryType.TWO_HOP)
            
        step1 = ReasoningStep(
            step_number=1,
            query=f"Xác định điểm bắt đầu: {entity_name}",
            result=entity,
            explanation=f"Tìm thấy {entity.label}: {entity.name}",
            entities_involved=[entity],
            relationships_found=[]
        )
        steps.append(step1)
        
        # Step 2: Get first hop relationships
        first_hop_rels = self.kg.get_entity_relationships(entity_name)
        first_hop_entities = list(set(rel.target for rel in first_hop_rels))[:10]
        
        step2 = ReasoningStep(
            step_number=2,
            query=f"Hop 1: Các thực thể liên quan trực tiếp đến {entity_name}",
            result=first_hop_entities,
            explanation=f"Tìm thấy {len(first_hop_entities)} thực thể ở hop 1",
            entities_involved=first_hop_entities,
            relationships_found=first_hop_rels[:10]
        )
        steps.append(step2)
        
        for rel in first_hop_rels[:5]:
            evidence.append(rel.to_text())
            
        # Step 3: Get second hop relationships
        second_hop_entities = []
        second_hop_rels = []
        
        for hop1_entity in first_hop_entities[:5]:
            rels = self.kg.get_entity_relationships(hop1_entity.name)
            second_hop_rels.extend(rels[:5])
            for rel in rels[:5]:
                if rel.target.name != entity_name:
                    second_hop_entities.append(rel.target)
                    
        second_hop_entities = list(set(e.name for e in second_hop_entities))[:20]
        
        step3 = ReasoningStep(
            step_number=3,
            query=f"Hop 2: Các thực thể cách {entity_name} 2 bước",
            result=second_hop_entities,
            explanation=f"Tìm thấy {len(second_hop_entities)} thực thể ở hop 2",
            entities_involved=[],
            relationships_found=second_hop_rels[:10]
        )
        steps.append(step3)
        
        for rel in second_hop_rels[:5]:
            evidence.append(rel.to_text())
            
        # Compose answer
        if second_hop_entities:
            answer = f"Qua 2 bước suy luận từ {entity_name}, tìm thấy các thực thể: {', '.join(second_hop_entities[:10])}"
            if len(second_hop_entities) > 10:
                answer += f" và {len(second_hop_entities) - 10} thực thể khác."
            confidence = 0.85
        else:
            answer = f"Không tìm thấy kết quả cho truy vấn 2-hop từ {entity_name}."
            confidence = 0.3
            
        return ReasoningChain(
            question=question,
            query_type=QueryType.TWO_HOP,
            steps=steps,
            final_answer=answer,
            confidence=confidence,
            evidence=evidence
        )
        
    def _reason_three_hop(self, question: str, entities: List[str]) -> ReasoningChain:
        """Reason about three-hop queries."""
        steps = []
        evidence = []
        
        if not entities:
            return self._no_entity_response(question, QueryType.THREE_HOP)
            
        entity_name = entities[0]
        entity = self.kg.get_entity_by_name(entity_name)
        
        if not entity:
            return self._entity_not_found_response(question, entity_name, QueryType.THREE_HOP)
            
        # Use subgraph extraction for 3-hop
        subgraph_entities, subgraph_rels = self.kg.get_subgraph(entity_name, hops=3)
        
        step1 = ReasoningStep(
            step_number=1,
            query=f"Trích xuất subgraph 3-hop từ {entity_name}",
            result=(subgraph_entities, subgraph_rels),
            explanation=f"Tìm thấy {len(subgraph_entities)} thực thể và {len(subgraph_rels)} mối quan hệ trong phạm vi 3 hop",
            entities_involved=subgraph_entities[:10],
            relationships_found=subgraph_rels[:10]
        )
        steps.append(step1)
        
        for rel in subgraph_rels[:10]:
            evidence.append(rel.to_text())
            
        # Filter and organize results
        entity_names = [e.name for e in subgraph_entities if e.name != entity_name][:20]
        
        answer = f"Trong phạm vi 3 bước từ {entity_name}, tìm thấy {len(subgraph_entities)} thực thể liên quan: {', '.join(entity_names[:10])}"
        
        return ReasoningChain(
            question=question,
            query_type=QueryType.THREE_HOP,
            steps=steps,
            final_answer=answer,
            confidence=0.8,
            evidence=evidence
        )
        
    def _reason_path_finding(self, question: str, entities: List[str]) -> ReasoningChain:
        """Find and explain path between two entities."""
        steps = []
        evidence = []
        
        if len(entities) < 2:
            return ReasoningChain(
                question=question,
                query_type=QueryType.PATH_FINDING,
                steps=[],
                final_answer="Cần ít nhất 2 thực thể để tìm đường đi.",
                confidence=0.0,
                evidence=[]
            )
            
        source_name, target_name = entities[0], entities[1]
        
        # Step 1: Find path
        path = self.kg.find_path(source_name, target_name)
        
        if path:
            step1 = ReasoningStep(
                step_number=1,
                query=f"Tìm đường đi từ {source_name} đến {target_name}",
                result=path,
                explanation=f"Tìm thấy đường đi với {len(path)} bước",
                entities_involved=path.get_entities(),
                relationships_found=path.relationships
            )
            steps.append(step1)
            
            evidence.append(path.to_text())
            
            answer = f"{source_name} và {target_name} được kết nối qua {len(path)} bước: {path.to_text()}"
            confidence = 0.95
        else:
            answer = f"Không tìm thấy đường đi giữa {source_name} và {target_name}."
            confidence = 0.5
            
        return ReasoningChain(
            question=question,
            query_type=QueryType.PATH_FINDING,
            steps=steps,
            final_answer=answer,
            confidence=confidence,
            evidence=evidence
        )
        
    def _reason_relationship(self, question: str, entities: List[str]) -> ReasoningChain:
        """Determine relationship between entities."""
        return self._reason_path_finding(question, entities)
        
    def _reason_aggregation(self, question: str, entities: List[str]) -> ReasoningChain:
        """Handle aggregation queries (counting, etc.)."""
        steps = []
        evidence = []
        
        if not entities:
            return self._no_entity_response(question, QueryType.AGGREGATION)
            
        entity_name = entities[0]
        
        # Get relationships and count
        relationships = self.kg.get_entity_relationships(entity_name)
        
        step1 = ReasoningStep(
            step_number=1,
            query=f"Đếm các mối quan hệ của {entity_name}",
            result=len(relationships),
            explanation=f"Tìm thấy {len(relationships)} mối quan hệ",
            entities_involved=[],
            relationships_found=relationships[:5]
        )
        steps.append(step1)
        
        # Group by relationship type
        rel_counts = {}
        for rel in relationships:
            rel_type = rel.relation_type
            rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
            
        count_text = ", ".join([f"{t}: {c}" for t, c in rel_counts.items()])
        answer = f"{entity_name} có {len(relationships)} mối quan hệ. Chi tiết: {count_text}"
        
        return ReasoningChain(
            question=question,
            query_type=QueryType.AGGREGATION,
            steps=steps,
            final_answer=answer,
            confidence=0.9,
            evidence=[f"Tổng số: {len(relationships)} mối quan hệ"]
        )
        
    def _reason_general(self, question: str, entities: List[str]) -> ReasoningChain:
        """Handle general queries."""
        if entities:
            return self._reason_entity_lookup(question, entities)
        return self._no_entity_response(question, QueryType.ENTITY_LOOKUP)
        
    def _get_relationship_types_from_question(self, question: str) -> List[str]:
        """Extract relationship types from question."""
        q = question.lower()
        rel_types = []
        
        for keyword, types in self.relation_keywords.items():
            if keyword in q:
                rel_types.extend(types)
                
        return list(set(rel_types))
        
    def _no_entity_response(self, question: str, query_type: QueryType) -> ReasoningChain:
        """Response when no entity found."""
        return ReasoningChain(
            question=question,
            query_type=query_type,
            steps=[],
            final_answer="Không tìm thấy thực thể nào trong câu hỏi. Vui lòng cung cấp tên cầu thủ, câu lạc bộ, hoặc đội tuyển cụ thể.",
            confidence=0.0,
            evidence=[]
        )
        
    def _entity_not_found_response(self, question: str, entity_name: str, 
                                    query_type: QueryType) -> ReasoningChain:
        """Response when entity not found in graph."""
        return ReasoningChain(
            question=question,
            query_type=query_type,
            steps=[],
            final_answer=f"Không tìm thấy '{entity_name}' trong đồ thị tri thức.",
            confidence=0.1,
            evidence=[]
        )
        
    def answer_yes_no(self, question: str, entities: List[str] = None) -> Tuple[bool, float, str]:
        """
        Answer a yes/no question.
        
        Returns:
            Tuple of (answer, confidence, explanation)
        """
        chain = self.reason(question, entities)
        
        # Check if evidence supports positive answer
        if chain.evidence and chain.confidence > 0.5:
            return True, chain.confidence, chain.final_answer
        return False, 1 - chain.confidence, chain.final_answer
        
    def verify_fact(self, subject: str, predicate: str, obj: str) -> Tuple[bool, float, List[str]]:
        """
        Verify a fact triple (subject, predicate, object).
        
        Returns:
            Tuple of (is_true, confidence, evidence)
        """
        # Get relationships of subject
        rels = self.kg.get_entity_relationships(subject)
        
        evidence = []
        for rel in rels:
            if rel.relation_type.lower() == predicate.lower() or \
               predicate.lower() in rel.relation_type.lower():
                if rel.target.name.lower() == obj.lower():
                    evidence.append(rel.to_text())
                    return True, 0.95, evidence
                    
        # Try finding path
        path = self.kg.find_path(subject, obj)
        if path and len(path) == 1:
            evidence.append(path.to_text())
            return True, 0.9, evidence
            
        return False, 0.1, ["Không tìm thấy bằng chứng"]
