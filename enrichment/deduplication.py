"""
Deduplication Module for Vietnam Football Knowledge Graph Enrichment

This module handles deduplication of entities and relations
against the existing knowledge graph.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EntityDeduplicator:
    """
    Deduplicates entities against existing knowledge graph.
    """
    
    def __init__(self, threshold: float = 0.90):
        """
        Initialize the deduplicator.
        
        Args:
            threshold: Similarity threshold for deduplication
        """
        self.threshold = threshold
        self._existing_entities: Dict[str, Set[str]] = {}  # type -> set of normalized names
    
    def add_existing(self, entity_type: str, name: str) -> None:
        """Add an existing entity to the dedup index."""
        if entity_type not in self._existing_entities:
            self._existing_entities[entity_type] = set()
        self._existing_entities[entity_type].add(self._normalize(name))
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return ' '.join(text.lower().split())
    
    def is_duplicate(
        self,
        text: str,
        entity_type: str,
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if an entity is a duplicate.
        
        Args:
            text: Entity text
            entity_type: Entity type
            
        Returns:
            Tuple of (is_duplicate, similarity_score)
        """
        norm_text = self._normalize(text)
        
        if entity_type not in self._existing_entities:
            return (False, None)
        
        # Exact match
        if norm_text in self._existing_entities[entity_type]:
            return (True, 1.0)
        
        # Fuzzy match
        try:
            from rapidfuzz import fuzz
            
            for existing in self._existing_entities[entity_type]:
                score = fuzz.token_set_ratio(norm_text, existing) / 100.0
                if score >= self.threshold:
                    return (True, score)
        except ImportError:
            pass
        
        return (False, None)


class RelationDeduplicator:
    """
    Deduplicates relations against existing knowledge graph.
    """
    
    def __init__(self, threshold: float = 0.95):
        """
        Initialize the deduplicator.
        
        Args:
            threshold: Threshold for relation matching
        """
        self.threshold = threshold
        self._existing_relations: Set[Tuple[int, str, int]] = set()  # (subj_id, pred, obj_id)
    
    def add_existing(
        self,
        subject_id: int,
        predicate: str,
        object_id: int,
    ) -> None:
        """Add an existing relation to the dedup index."""
        self._existing_relations.add((subject_id, predicate, object_id))
    
    def is_duplicate(
        self,
        subject_id: Optional[int],
        predicate: str,
        object_id: Optional[int],
    ) -> bool:
        """
        Check if a relation is a duplicate.
        
        Args:
            subject_id: Subject wiki_id
            predicate: Relation type
            object_id: Object wiki_id
            
        Returns:
            True if duplicate
        """
        if subject_id is None or object_id is None:
            return False
        
        return (subject_id, predicate, object_id) in self._existing_relations
