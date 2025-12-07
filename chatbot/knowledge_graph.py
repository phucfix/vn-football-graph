"""
Knowledge Graph Interface for Vietnam Football Graph

This module provides the interface to query and traverse the Neo4j knowledge graph.
Supports:
- Entity lookup
- Relationship traversal
- Multi-hop path finding
- Subgraph extraction
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from .config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MAX_HOPS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents a node in the knowledge graph."""
    id: str
    name: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self):
        return f"{self.label}:{self.name}"
    
    def to_text(self) -> str:
        """Convert entity to natural language text."""
        props = ", ".join([f"{k}: {v}" for k, v in self.properties.items() if v])
        if props:
            return f"{self.name} (loại: {self.label}, {props})"
        return f"{self.name} (loại: {self.label})"


@dataclass 
class Relationship:
    """Represents an edge in the knowledge graph."""
    source: Entity
    relation_type: str
    target: Entity
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self):
        return f"({self.source.name})-[{self.relation_type}]->({self.target.name})"
    
    def to_text(self) -> str:
        """Convert relationship to natural language text."""
        relation_map = {
            "PLAYED_FOR": "đã chơi cho",
            "PLAYED_FOR_NATIONAL": "đã khoác áo đội tuyển",
            "TEAMMATE": "là đồng đội của",
            "NATIONAL_TEAMMATE": "là đồng đội tuyển quốc gia với",
            "COACHED": "đã huấn luyện",
            "COACHED_NATIONAL": "đã huấn luyện đội tuyển",
            "BORN_IN": "sinh ra tại",
            "FROM_PROVINCE": "đến từ",
            "BASED_IN": "đặt trụ sở tại",
            "HOME_STADIUM": "có sân nhà là",
            "COMPETED_IN": "tham gia giải đấu",
            "COMPETES_IN": "thi đấu tại",
            "PLAYED_SAME_CLUBS": "từng chơi cùng câu lạc bộ với",
            "SAME_PROVINCE": "cùng quê với",
            "HAS_POSITION": "chơi ở vị trí",
            "HAS_NATIONALITY": "mang quốc tịch",
        }
        
        rel_text = relation_map.get(self.relation_type, self.relation_type.lower().replace("_", " "))
        return f"{self.source.name} {rel_text} {self.target.name}"


@dataclass
class Path:
    """Represents a path (sequence of relationships) in the graph."""
    relationships: List[Relationship]
    
    def __len__(self):
        return len(self.relationships)
    
    def to_text(self) -> str:
        """Convert path to natural language."""
        if not self.relationships:
            return ""
        texts = [rel.to_text() for rel in self.relationships]
        return " → ".join(texts)
    
    def get_entities(self) -> List[Entity]:
        """Get all unique entities in the path."""
        entities = []
        seen = set()
        for rel in self.relationships:
            if rel.source.id not in seen:
                entities.append(rel.source)
                seen.add(rel.source.id)
            if rel.target.id not in seen:
                entities.append(rel.target)
                seen.add(rel.target.id)
        return entities


class KnowledgeGraph:
    """
    Interface to the Vietnam Football Knowledge Graph in Neo4j.
    """
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.driver = None
        
    def connect(self) -> bool:
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("✅ Connected to Knowledge Graph")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False
            
    def close(self):
        """Close the connection."""
        if self.driver:
            self.driver.close()
            
    def _node_to_entity(self, node) -> Entity:
        """Convert Neo4j node to Entity."""
        props = dict(node)
        name = props.pop('name', props.pop('title', str(node.element_id)))
        labels = list(node.labels)
        label = labels[0] if labels else "Unknown"
        return Entity(
            id=str(node.element_id),
            name=name,
            label=label,
            properties=props
        )
        
    def search_entities(self, search_term: str, limit: int = 10) -> List[Entity]:
        """
        Search for entities by name (fuzzy matching).
        """
        with self.driver.session() as session:
            # Use CONTAINS for fuzzy matching
            result = session.run("""
                MATCH (n)
                WHERE n.name IS NOT NULL 
                AND (toLower(n.name) CONTAINS toLower($search_term)
                     OR toLower($search_term) CONTAINS toLower(n.name))
                RETURN n, labels(n)[0] as label
                ORDER BY 
                    CASE WHEN toLower(n.name) = toLower($search_term) THEN 0
                         WHEN toLower(n.name) STARTS WITH toLower($search_term) THEN 1
                         ELSE 2 END,
                    size(n.name)
                LIMIT $limit
            """, search_term=search_term, limit=limit)
            
            entities = []
            for record in result:
                entities.append(self._node_to_entity(record['n']))
            return entities
            
    def get_entity_by_name(self, name: str, label: str = None) -> Optional[Entity]:
        """
        Get exact entity by name.
        """
        with self.driver.session() as session:
            if label:
                result = session.run(f"""
                    MATCH (n:{label})
                    WHERE toLower(n.name) = toLower($name)
                    RETURN n
                    LIMIT 1
                """, name=name)
            else:
                result = session.run("""
                    MATCH (n)
                    WHERE toLower(n.name) = toLower($name)
                    RETURN n
                    LIMIT 1
                """, name=name)
                
            record = result.single()
            if record:
                return self._node_to_entity(record['n'])
            return None
            
    def get_entity_relationships(self, entity_name: str, direction: str = "both", 
                                  rel_types: List[str] = None) -> List[Relationship]:
        """
        Get all relationships of an entity.
        
        Args:
            entity_name: Name of the entity
            direction: "outgoing", "incoming", or "both"
            rel_types: Filter by relationship types
        """
        with self.driver.session() as session:
            rel_filter = ""
            if rel_types:
                rel_filter = ":" + "|".join(rel_types)
                
            if direction == "outgoing":
                query = f"""
                    MATCH (n)-[r{rel_filter}]->(m)
                    WHERE toLower(n.name) = toLower($name)
                    RETURN n, r, m
                    LIMIT 100
                """
            elif direction == "incoming":
                query = f"""
                    MATCH (n)<-[r{rel_filter}]-(m)
                    WHERE toLower(n.name) = toLower($name)
                    RETURN m as n, r, n as m
                    LIMIT 100
                """
            else:
                query = f"""
                    MATCH (n)-[r{rel_filter}]-(m)
                    WHERE toLower(n.name) = toLower($name)
                    RETURN n, r, m
                    LIMIT 100
                """
                
            result = session.run(query, name=entity_name)
            
            relationships = []
            for record in result:
                source = self._node_to_entity(record['n'])
                target = self._node_to_entity(record['m'])
                rel = Relationship(
                    source=source,
                    relation_type=record['r'].type,
                    target=target,
                    properties=dict(record['r'])
                )
                relationships.append(rel)
                
            return relationships
            
    def find_path(self, source_name: str, target_name: str, 
                  max_hops: int = None) -> Optional[Path]:
        """
        Find shortest path between two entities.
        """
        max_hops = max_hops or MAX_HOPS
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (source), (target)
                WHERE toLower(source.name) = toLower($source_name)
                AND toLower(target.name) = toLower($target_name)
                MATCH path = shortestPath((source)-[*..%d]-(target))
                RETURN path
                LIMIT 1
            """ % max_hops, source_name=source_name, target_name=target_name)
            
            record = result.single()
            if not record:
                return None
                
            neo4j_path = record['path']
            relationships = []
            
            nodes = list(neo4j_path.nodes)
            rels = list(neo4j_path.relationships)
            
            for i, rel in enumerate(rels):
                source = self._node_to_entity(nodes[i])
                target = self._node_to_entity(nodes[i + 1])
                relationships.append(Relationship(
                    source=source,
                    relation_type=rel.type,
                    target=target,
                    properties=dict(rel)
                ))
                
            return Path(relationships=relationships)
            
    def find_all_paths(self, source_name: str, target_name: str,
                       max_hops: int = None, limit: int = 5) -> List[Path]:
        """
        Find all paths between two entities.
        """
        max_hops = max_hops or MAX_HOPS
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (source), (target)
                WHERE toLower(source.name) = toLower($source_name)
                AND toLower(target.name) = toLower($target_name)
                MATCH path = (source)-[*1..%d]-(target)
                RETURN path
                ORDER BY length(path)
                LIMIT $limit
            """ % max_hops, source_name=source_name, target_name=target_name, limit=limit)
            
            paths = []
            for record in result:
                neo4j_path = record['path']
                relationships = []
                
                nodes = list(neo4j_path.nodes)
                rels = list(neo4j_path.relationships)
                
                for i, rel in enumerate(rels):
                    source = self._node_to_entity(nodes[i])
                    target = self._node_to_entity(nodes[i + 1])
                    relationships.append(Relationship(
                        source=source,
                        relation_type=rel.type,
                        target=target,
                        properties=dict(rel)
                    ))
                    
                paths.append(Path(relationships=relationships))
                
            return paths
            
    def get_subgraph(self, entity_name: str, hops: int = 1) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract a subgraph around an entity.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (center)
                WHERE toLower(center.name) = toLower($name)
                CALL {
                    WITH center
                    MATCH (center)-[r*1..%d]-(connected)
                    RETURN connected, r
                }
                WITH center, collect(DISTINCT connected) as nodes, collect(r) as rels
                RETURN center, nodes, rels
            """ % hops, name=entity_name)
            
            record = result.single()
            if not record:
                return [], []
                
            entities = [self._node_to_entity(record['center'])]
            for node in record['nodes']:
                entities.append(self._node_to_entity(node))
                
            # Get relationships separately
            relationships = self.get_entity_relationships(entity_name)
            
            return entities, relationships
            
    def execute_cypher(self, cypher_query: str, params: Dict = None) -> List[Dict]:
        """
        Execute a raw Cypher query.
        """
        with self.driver.session() as session:
            result = session.run(cypher_query, params or {})
            return [dict(record) for record in result]
            
    def get_entity_types(self) -> List[str]:
        """Get all entity types (labels) in the graph."""
        with self.driver.session() as session:
            result = session.run("CALL db.labels() YIELD label RETURN label")
            return [record['label'] for record in result]
            
    def get_relationship_types(self) -> List[str]:
        """Get all relationship types in the graph."""
        with self.driver.session() as session:
            result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
            return [record['relationshipType'] for record in result]
            
    def get_statistics(self) -> Dict:
        """Get graph statistics."""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
            return {
                "total_nodes": node_count,
                "total_relationships": rel_count,
                "entity_types": self.get_entity_types(),
                "relationship_types": self.get_relationship_types()
            }
    
    def check_same_club(self, player1: str, player2: str) -> Tuple[bool, Optional[str]]:
        """
        Check if two players played for the same club (2-hop query).
        Returns (True/False, club_name or None)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player)
                WHERE toLower(p1.name) CONTAINS toLower($player1)
                AND toLower(p2.name) CONTAINS toLower($player2)
                RETURN c.name as club
                LIMIT 1
            """, player1=player1, player2=player2)
            
            record = result.single()
            if record:
                return True, record['club']
            return False, None
    
    def check_same_province_via_club(self, player1: str, player2: str) -> Tuple[bool, Optional[str]]:
        """
        Check if player1 played for a club in the same province as player2 (3-hop query).
        Pattern: Player1 -> Club -> Province <- Player2 (birth)
        """
        with self.driver.session() as session:
            # Check multiple patterns for province connection
            result = session.run("""
                MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)-[:BASED_IN|LOCATED_IN]->(prov:Province)
                WHERE toLower(p1.name) CONTAINS toLower($player1)
                WITH p1, c, prov
                MATCH (p2:Player)-[:BORN_IN|FROM_PROVINCE]->(prov)
                WHERE toLower(p2.name) CONTAINS toLower($player2)
                RETURN prov.name as province, c.name as club
                LIMIT 1
            """, player1=player1, player2=player2)
            
            record = result.single()
            if record:
                return True, record['province']
            
            # Try alternative: both players from same province
            result = session.run("""
                MATCH (p1:Player)-[:BORN_IN|FROM_PROVINCE]->(prov:Province)<-[:BORN_IN|FROM_PROVINCE]-(p2:Player)
                WHERE toLower(p1.name) CONTAINS toLower($player1)
                AND toLower(p2.name) CONTAINS toLower($player2)
                RETURN prov.name as province
                LIMIT 1
            """, player1=player1, player2=player2)
            
            record = result.single()
            if record:
                return True, record['province']
                
            return False, None
    
    def check_played_in_province_of_player(self, player1: str, player2: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if player1 played for a club in a province where player2 is from (3-hop).
        Returns (True/False, club_name, province_name)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p2:Player)-[:BORN_IN|FROM_PROVINCE]->(prov:Province)
                WHERE toLower(p2.name) CONTAINS toLower($player2)
                WITH prov
                MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club)-[:BASED_IN|LOCATED_IN]->(prov)
                WHERE toLower(p1.name) CONTAINS toLower($player1)
                RETURN c.name as club, prov.name as province
                LIMIT 1
            """, player1=player1, player2=player2)
            
            record = result.single()
            if record:
                return True, record['club'], record['province']
            return False, None, None
    
    def check_teammates(self, player1: str, player2: str) -> Tuple[bool, Optional[str]]:
        """
        Check if two players are/were teammates (direct relationship or via same club).
        """
        with self.driver.session() as session:
            # Direct TEAMMATE relationship
            result = session.run("""
                MATCH (p1:Player)-[:TEAMMATE|NATIONAL_TEAMMATE]-(p2:Player)
                WHERE toLower(p1.name) CONTAINS toLower($player1)
                AND toLower(p2.name) CONTAINS toLower($player2)
                RETURN 'direct' as type
                LIMIT 1
            """, player1=player1, player2=player2)
            
            if result.single():
                return True, "direct_teammate"
            
            # Via same club
            same_club, club = self.check_same_club(player1, player2)
            if same_club:
                return True, club
                
            return False, None
    
    def get_player_clubs(self, player_name: str) -> List[str]:
        """Get all clubs a player played for."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
                WHERE toLower(p.name) CONTAINS toLower($player_name)
                RETURN c.name as club
            """, player_name=player_name)
            
            return [record['club'] for record in result]
    
    def get_player_province(self, player_name: str) -> Optional[str]:
        """Get the province a player is from."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Player)-[:BORN_IN|FROM_PROVINCE]->(prov:Province)
                WHERE toLower(p.name) CONTAINS toLower($player_name)
                RETURN prov.name as province
                LIMIT 1
            """, player_name=player_name)
            
            record = result.single()
            return record['province'] if record else None
    
    def get_club_province(self, club_name: str) -> Optional[str]:
        """Get the province where a club is based."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Club)-[:BASED_IN|LOCATED_IN]->(prov:Province)
                WHERE toLower(c.name) CONTAINS toLower($club_name)
                RETURN prov.name as province
                LIMIT 1
            """, club_name=club_name)
            
            record = result.single()
            return record['province'] if record else None
            
            record = result.single()
            return record['province'] if record else None


# Convenience functions
def get_kg() -> KnowledgeGraph:
    """Get a connected KnowledgeGraph instance."""
    kg = KnowledgeGraph()
    kg.connect()
    return kg
