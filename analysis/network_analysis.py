"""
Network Analysis for Vietnam Football Knowledge Graph

This module implements social network analysis algorithms:
1. Small World Analysis - Average shortest path length
2. Graph Ranking - PageRank algorithm
3. Community Detection - Louvain algorithm

Requires: Neo4j Graph Data Science (GDS) library installed on Neo4j server
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / '.env')

from config.config import (
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    REPORTS_DIR,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """
    Social Network Analysis for Vietnam Football Knowledge Graph.
    
    Implements:
    - Small World Analysis (Average Shortest Path Length)
    - PageRank for node ranking
    - Community Detection using Louvain algorithm
    """
    
    def __init__(self, uri: str, user: str, password: str):
        """Initialize connection to Neo4j."""
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "small_world": {},
            "pagerank": {},
            "community_detection": {},
            "graph_stats": {}
        }
        
    def connect(self) -> bool:
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info("✅ Connected to Neo4j successfully")
            return True
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            return False
            
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Connection closed")
            
    def get_graph_statistics(self) -> Dict:
        """Get basic graph statistics."""
        logger.info("\n" + "="*60)
        logger.info("📊 GRAPH STATISTICS")
        logger.info("="*60)
        
        with self.driver.session() as session:
            # Count nodes by label
            node_counts = session.run("""
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {})
                YIELD value
                RETURN label, value.count as count
                ORDER BY value.count DESC
            """).data()
            
            # If APOC not available, use alternative
            if not node_counts:
                node_counts = []
                labels_result = session.run("CALL db.labels() YIELD label RETURN label").data()
                for label_row in labels_result:
                    label = label_row['label']
                    count = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count").single()['count']
                    node_counts.append({"label": label, "count": count})
            
            # Count relationships by type
            rel_counts = session.run("""
                CALL db.relationshipTypes() YIELD relationshipType as type
                RETURN type, 0 as count
            """).data()
            
            # Get actual counts
            rel_counts = []
            rel_types = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType").data()
            for rel_row in rel_types:
                rel_type = rel_row['relationshipType']
                count = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count").single()['count']
                rel_counts.append({"type": rel_type, "count": count})
            
            # Total counts
            total_nodes = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            total_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
        stats = {
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "nodes_by_label": {item['label']: item['count'] for item in node_counts},
            "relationships_by_type": {item['type']: item['count'] for item in rel_counts}
        }
        
        logger.info(f"\n📌 Total Nodes: {total_nodes:,}")
        logger.info(f"📌 Total Relationships: {total_rels:,}")
        
        logger.info("\n📌 Nodes by Label:")
        for label, count in stats['nodes_by_label'].items():
            logger.info(f"   - {label}: {count:,}")
            
        logger.info("\n📌 Relationships by Type:")
        for rel_type, count in sorted(stats['relationships_by_type'].items(), key=lambda x: -x[1])[:10]:
            logger.info(f"   - {rel_type}: {count:,}")
            
        self.results['graph_stats'] = stats
        return stats
        
    def analyze_small_world(self, sample_size: int = 1000) -> Dict:
        """
        Analyze Small World properties of the network.
        
        Small World networks have:
        1. Short average path length (like random networks)
        2. High clustering coefficient (like regular lattices)
        
        We focus on the Player-Player network via TEAMMATE relationships.
        """
        logger.info("\n" + "="*60)
        logger.info("🌍 SMALL WORLD ANALYSIS")
        logger.info("="*60)
        
        with self.driver.session() as session:
            # First, check if GDS is available
            gds_available = self._check_gds_available(session)
            
            if gds_available:
                return self._analyze_small_world_gds(session, sample_size)
            else:
                return self._analyze_small_world_native(session, sample_size)
                
    def _check_gds_available(self, session) -> bool:
        """Check if Graph Data Science library is available."""
        try:
            session.run("RETURN gds.version()").single()
            logger.info("✅ GDS library detected")
            return True
        except:
            logger.info("⚠️ GDS library not available, using native Cypher")
            return False
            
    def _analyze_small_world_gds(self, session, sample_size: int) -> Dict:
        """Use GDS for small world analysis."""
        # Create projection for player network
        try:
            session.run("CALL gds.graph.drop('playerNetwork', false)")
        except:
            pass
            
        # Project the graph - using TEAMMATE relationships
        session.run("""
            CALL gds.graph.project(
                'playerNetwork',
                'Player',
                {
                    TEAMMATE: {
                        type: 'TEAMMATE',
                        orientation: 'UNDIRECTED'
                    }
                }
            )
        """)
        
        # Calculate average shortest path using sampling
        result = session.run("""
            CALL gds.allShortestPaths.stream('playerNetwork', {})
            YIELD sourceNodeId, targetNodeId, distance
            WHERE distance > 0 AND distance < infinity
            RETURN 
                avg(distance) as avgPathLength,
                max(distance) as diameter,
                count(*) as pathsAnalyzed
        """).single()
        
        avg_path = result['avgPathLength']
        diameter = result['diameter']
        paths_count = result['pathsAnalyzed']
        
        # Calculate clustering coefficient
        clustering_result = session.run("""
            CALL gds.localClusteringCoefficient.stream('playerNetwork')
            YIELD nodeId, localClusteringCoefficient
            WHERE localClusteringCoefficient > 0
            RETURN avg(localClusteringCoefficient) as avgClustering
        """).single()
        
        avg_clustering = clustering_result['avgClustering'] if clustering_result else 0
        
        # Cleanup
        session.run("CALL gds.graph.drop('playerNetwork', false)")
        
        small_world_results = {
            "average_path_length": avg_path,
            "network_diameter": diameter,
            "paths_analyzed": paths_count,
            "clustering_coefficient": avg_clustering,
            "is_small_world": avg_path < 6 and avg_clustering > 0.1  # Six degrees of separation
        }
        
        self._log_small_world_results(small_world_results)
        self.results['small_world'] = small_world_results
        return small_world_results
        
    def _analyze_small_world_native(self, session, sample_size: int) -> Dict:
        """Use native Cypher for small world analysis (without GDS)."""
        logger.info(f"\n🔍 Analyzing shortest paths (sampling {sample_size} pairs)...")
        
        # Get player count
        player_count = session.run("""
            MATCH (p:Player) RETURN count(p) as count
        """).single()['count']
        
        logger.info(f"   Total players in network: {player_count:,}")
        
        # Sample random pairs and calculate shortest paths
        # Using TEAMMATE relationships for social network
        path_lengths = []
        
        # Get shortest paths between random player pairs
        result = session.run(f"""
            MATCH (p1:Player)
            WITH p1, rand() as r1
            ORDER BY r1
            LIMIT {min(sample_size, player_count // 2)}
            MATCH (p2:Player)
            WHERE p1 <> p2
            WITH p1, p2, rand() as r2
            ORDER BY r2
            LIMIT 1
            MATCH path = shortestPath((p1)-[:TEAMMATE|PLAYED_SAME_CLUB*..10]-(p2))
            RETURN p1.name as player1, p2.name as player2, length(path) as pathLength
        """).data()
        
        if not result:
            # Try with different relationship types
            result = session.run(f"""
                MATCH (p1:Player)
                WITH p1, rand() as r1
                ORDER BY r1
                LIMIT {min(sample_size, player_count // 2)}
                MATCH (p2:Player)
                WHERE p1 <> p2
                WITH p1, p2, rand() as r2
                ORDER BY r2
                LIMIT 1
                MATCH path = shortestPath((p1)-[*..10]-(p2))
                RETURN p1.name as player1, p2.name as player2, length(path) as pathLength
            """).data()
        
        path_lengths = [r['pathLength'] for r in result if r['pathLength'] is not None]
        
        # Calculate more comprehensive paths
        logger.info("   Calculating paths between multiple node pairs...")
        comprehensive_result = session.run("""
            MATCH (p1:Player)
            WITH collect(p1) as players
            UNWIND range(0, size(players)-1) as i
            UNWIND range(i+1, size(players)-1) as j
            WITH players[i] as p1, players[j] as p2
            WHERE rand() < 0.01  // Sample 1% of pairs
            MATCH path = shortestPath((p1)-[*..15]-(p2))
            WHERE path IS NOT NULL
            RETURN 
                avg(length(path)) as avgPathLength,
                max(length(path)) as maxPathLength,
                min(length(path)) as minPathLength,
                count(path) as pathsFound
            LIMIT 1
        """).single()
        
        if comprehensive_result and comprehensive_result['pathsFound'] > 0:
            avg_path = comprehensive_result['avgPathLength']
            max_path = comprehensive_result['maxPathLength']
            min_path = comprehensive_result['minPathLength']
            paths_found = comprehensive_result['pathsFound']
        else:
            avg_path = sum(path_lengths) / len(path_lengths) if path_lengths else 0
            max_path = max(path_lengths) if path_lengths else 0
            min_path = min(path_lengths) if path_lengths else 0
            paths_found = len(path_lengths)
        
        # Calculate clustering coefficient approximation
        logger.info("   Calculating clustering coefficient...")
        clustering_result = session.run("""
            MATCH (p:Player)-[:TEAMMATE|PLAYED_SAME_CLUB]-(neighbor)
            WITH p, collect(DISTINCT neighbor) as neighbors
            WHERE size(neighbors) > 1
            UNWIND neighbors as n1
            UNWIND neighbors as n2
            WITH p, neighbors, n1, n2
            WHERE id(n1) < id(n2)
            OPTIONAL MATCH (n1)-[:TEAMMATE|PLAYED_SAME_CLUB]-(n2)
            WITH p, size(neighbors) as degree, 
                 count(CASE WHEN n1 IS NOT NULL AND n2 IS NOT NULL THEN 1 END) as triangles,
                 size(neighbors) * (size(neighbors) - 1) / 2 as possibleTriangles
            WHERE possibleTriangles > 0
            RETURN avg(toFloat(triangles) / possibleTriangles) as avgClustering
        """).single()
        
        avg_clustering = clustering_result['avgClustering'] if clustering_result and clustering_result['avgClustering'] else 0
        
        small_world_results = {
            "average_path_length": round(avg_path, 3) if avg_path else 0,
            "network_diameter": max_path,
            "min_path_length": min_path,
            "paths_analyzed": paths_found,
            "clustering_coefficient": round(avg_clustering, 4) if avg_clustering else 0,
            "is_small_world": avg_path < 6 if avg_path else False,  # Six degrees of separation
            "player_count": player_count
        }
        
        self._log_small_world_results(small_world_results)
        self.results['small_world'] = small_world_results
        return small_world_results
        
    def _log_small_world_results(self, results: Dict):
        """Log small world analysis results."""
        logger.info("\n📊 Small World Analysis Results:")
        logger.info(f"   • Average Shortest Path Length: {results.get('average_path_length', 'N/A')}")
        logger.info(f"   • Network Diameter (max path): {results.get('network_diameter', 'N/A')}")
        logger.info(f"   • Clustering Coefficient: {results.get('clustering_coefficient', 'N/A')}")
        logger.info(f"   • Paths Analyzed: {results.get('paths_analyzed', 'N/A'):,}")
        
        if results.get('is_small_world'):
            logger.info("\n   ✅ This network exhibits SMALL WORLD properties!")
            logger.info("   • Short average path length (< 6 degrees of separation)")
        else:
            logger.info("\n   ⚠️ Small world property not confirmed")
            
    def calculate_pagerank(self, top_n: int = 20) -> Dict:
        """
        Calculate PageRank for all nodes to identify important entities.
        """
        logger.info("\n" + "="*60)
        logger.info("📊 PAGERANK ANALYSIS")
        logger.info("="*60)
        
        with self.driver.session() as session:
            gds_available = self._check_gds_available(session)
            
            if gds_available:
                return self._calculate_pagerank_gds(session, top_n)
            else:
                return self._calculate_pagerank_native(session, top_n)
                
    def _calculate_pagerank_gds(self, session, top_n: int) -> Dict:
        """Use GDS for PageRank calculation."""
        # Drop existing projection if exists
        try:
            session.run("CALL gds.graph.drop('fullGraph', false)")
        except:
            pass
            
        # Create graph projection with all nodes and relationships
        session.run("""
            CALL gds.graph.project(
                'fullGraph',
                '*',
                '*'
            )
        """)
        
        # Run PageRank
        result = session.run(f"""
            CALL gds.pageRank.stream('fullGraph')
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).name as name,
                   labels(gds.util.asNode(nodeId))[0] as label,
                   score
            ORDER BY score DESC
            LIMIT {top_n}
        """).data()
        
        # Cleanup
        session.run("CALL gds.graph.drop('fullGraph', false)")
        
        return self._process_pagerank_results(result, session, top_n)
        
    def _calculate_pagerank_native(self, session, top_n: int) -> Dict:
        """Calculate PageRank-like scores using native Cypher (degree centrality)."""
        logger.info("\n🔍 Calculating centrality scores (native method)...")
        
        # For each node type, calculate degree centrality (simpler but related to PageRank)
        # Players
        player_scores = session.run(f"""
            MATCH (p:Player)
            OPTIONAL MATCH (p)-[r]-()
            WITH p, count(DISTINCT r) as degree
            RETURN p.name as name, 'Player' as label, 
                   toFloat(degree) as score
            ORDER BY degree DESC
            LIMIT {top_n}
        """).data()
        
        # Clubs
        club_scores = session.run(f"""
            MATCH (c:Club)
            OPTIONAL MATCH (c)-[r]-()
            WITH c, count(DISTINCT r) as degree
            RETURN c.name as name, 'Club' as label,
                   toFloat(degree) as score
            ORDER BY degree DESC
            LIMIT {top_n}
        """).data()
        
        # Coaches
        coach_scores = session.run(f"""
            MATCH (c:Coach)
            OPTIONAL MATCH (c)-[r]-()
            WITH c, count(DISTINCT r) as degree
            RETURN c.name as name, 'Coach' as label,
                   toFloat(degree) as score
            ORDER BY degree DESC
            LIMIT {top_n}
        """).data()
        
        # National Teams
        national_scores = session.run(f"""
            MATCH (n:NationalTeam)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(DISTINCT r) as degree
            RETURN n.name as name, 'NationalTeam' as label,
                   toFloat(degree) as score
            ORDER BY degree DESC
            LIMIT {top_n}
        """).data()
        
        # Provinces
        province_scores = session.run(f"""
            MATCH (p:Province)
            OPTIONAL MATCH (p)-[r]-()
            WITH p, count(DISTINCT r) as degree
            RETURN p.name as name, 'Province' as label,
                   toFloat(degree) as score
            ORDER BY degree DESC
            LIMIT {top_n}
        """).data()
        
        # Combine and sort all results
        all_scores = player_scores + club_scores + coach_scores + national_scores + province_scores
        all_scores.sort(key=lambda x: -x['score'])
        
        return self._process_pagerank_results(all_scores[:top_n * 2], session, top_n)
        
    def _process_pagerank_results(self, results: List[Dict], session, top_n: int) -> Dict:
        """Process and log PageRank results."""
        # Group by label
        by_label = {}
        for item in results:
            label = item['label']
            if label not in by_label:
                by_label[label] = []
            by_label[label].append({
                "name": item['name'],
                "score": round(item['score'], 6) if item['score'] else 0
            })
            
        # Normalize scores for each category
        for label in by_label:
            items = by_label[label]
            if items:
                max_score = max(item['score'] for item in items) or 1
                for item in items:
                    item['normalized_score'] = round(item['score'] / max_score, 4)
                    
        pagerank_results = {
            "top_overall": results[:top_n],
            "top_by_category": by_label
        }
        
        # Log results
        logger.info("\n📊 PageRank / Centrality Results:")
        
        logger.info(f"\n🏆 Top {min(top_n, len(results))} Most Important Nodes Overall:")
        for i, item in enumerate(results[:top_n], 1):
            logger.info(f"   {i:2}. [{item['label']:12}] {item['name'][:40]:40} (score: {item['score']:.4f})")
            
        for label, items in by_label.items():
            if items:
                logger.info(f"\n🏆 Top {min(5, len(items))} {label}s:")
                for i, item in enumerate(items[:5], 1):
                    logger.info(f"   {i}. {item['name'][:40]:40} (score: {item['score']:.4f})")
                    
        self.results['pagerank'] = pagerank_results
        return pagerank_results
        
    def detect_communities(self, min_community_size: int = 3) -> Dict:
        """
        Detect communities in the network using Louvain algorithm.
        Focus on player communities based on team relationships.
        """
        logger.info("\n" + "="*60)
        logger.info("👥 COMMUNITY DETECTION")
        logger.info("="*60)
        
        with self.driver.session() as session:
            gds_available = self._check_gds_available(session)
            
            if gds_available:
                return self._detect_communities_gds(session, min_community_size)
            else:
                return self._detect_communities_native(session, min_community_size)
                
    def _detect_communities_gds(self, session, min_community_size: int) -> Dict:
        """Use GDS Louvain for community detection."""
        try:
            session.run("CALL gds.graph.drop('communityGraph', false)")
        except:
            pass
            
        # Project graph for community detection
        session.run("""
            CALL gds.graph.project(
                'communityGraph',
                ['Player', 'Club'],
                {
                    PLAYED_FOR: {orientation: 'UNDIRECTED'},
                    TEAMMATE: {orientation: 'UNDIRECTED'}
                }
            )
        """)
        
        # Run Louvain
        result = session.run("""
            CALL gds.louvain.stream('communityGraph')
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).name as name,
                   labels(gds.util.asNode(nodeId))[0] as label,
                   communityId
            ORDER BY communityId
        """).data()
        
        # Cleanup
        session.run("CALL gds.graph.drop('communityGraph', false)")
        
        return self._process_community_results(result, min_community_size)
        
    def _detect_communities_native(self, session, min_community_size: int) -> Dict:
        """Detect communities using native Cypher (connected components approach)."""
        logger.info("\n🔍 Detecting communities using club-based clustering...")
        
        # Group players by their clubs (natural communities)
        club_communities = session.run("""
            MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
            WITH c, collect(DISTINCT p.name) as players
            WHERE size(players) >= $min_size
            RETURN c.name as community_name, 
                   'Club' as community_type,
                   players,
                   size(players) as size
            ORDER BY size DESC
        """, min_size=min_community_size).data()
        
        # Group players by national team (another community type)
        national_communities = session.run("""
            MATCH (p:Player)-[:PLAYED_FOR_NATIONAL]->(n:NationalTeam)
            WITH n, collect(DISTINCT p.name) as players
            WHERE size(players) >= $min_size
            RETURN n.name as community_name,
                   'NationalTeam' as community_type,
                   players,
                   size(players) as size
            ORDER BY size DESC
        """, min_size=min_community_size).data()
        
        # Group players by province (geographic community)
        province_communities = session.run("""
            MATCH (p:Player)-[:BORN_IN|PLAYER_FROM_PROVINCE]->(pr:Province)
            WITH pr, collect(DISTINCT p.name) as players
            WHERE size(players) >= $min_size
            RETURN pr.name as community_name,
                   'Province' as community_type,
                   players,
                   size(players) as size
            ORDER BY size DESC
        """, min_size=min_community_size).data()
        
        # Find overlapping players (belong to multiple communities)
        overlapping = session.run("""
            MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club)
            MATCH (p)-[:PLAYED_FOR]->(c2:Club)
            WHERE c1 <> c2
            WITH p, collect(DISTINCT c1.name) + collect(DISTINCT c2.name) as clubs
            WHERE size(clubs) > 1
            RETURN p.name as player, clubs
            ORDER BY size(clubs) DESC
            LIMIT 20
        """).data()
        
        all_communities = {
            "club_communities": club_communities,
            "national_communities": national_communities,
            "province_communities": province_communities,
            "multi_club_players": overlapping
        }
        
        return self._process_community_results_native(all_communities, min_community_size)
        
    def _process_community_results(self, results: List[Dict], min_community_size: int) -> Dict:
        """Process GDS community detection results."""
        communities = {}
        for item in results:
            comm_id = item['communityId']
            if comm_id not in communities:
                communities[comm_id] = {"members": [], "labels": set()}
            communities[comm_id]["members"].append(item['name'])
            communities[comm_id]["labels"].add(item['label'])
            
        # Filter by size and convert sets to lists
        filtered = {
            k: {"members": v["members"], "labels": list(v["labels"]), "size": len(v["members"])}
            for k, v in communities.items()
            if len(v["members"]) >= min_community_size
        }
        
        community_results = {
            "total_communities": len(filtered),
            "communities": filtered,
            "size_distribution": {
                "min": min(len(c["members"]) for c in filtered.values()) if filtered else 0,
                "max": max(len(c["members"]) for c in filtered.values()) if filtered else 0,
                "avg": sum(len(c["members"]) for c in filtered.values()) / len(filtered) if filtered else 0
            }
        }
        
        self._log_community_results(community_results)
        self.results['community_detection'] = community_results
        return community_results
        
    def _process_community_results_native(self, all_communities: Dict, min_community_size: int) -> Dict:
        """Process native community detection results."""
        club_comms = all_communities['club_communities']
        national_comms = all_communities['national_communities']
        province_comms = all_communities['province_communities']
        overlapping = all_communities['multi_club_players']
        
        community_results = {
            "total_club_communities": len(club_comms),
            "total_national_communities": len(national_comms),
            "total_province_communities": len(province_comms),
            "club_communities": [
                {"name": c['community_name'], "size": c['size'], "top_members": c['players'][:10]}
                for c in club_comms[:20]
            ],
            "national_communities": [
                {"name": c['community_name'], "size": c['size'], "top_members": c['players'][:10]}
                for c in national_comms[:10]
            ],
            "province_communities": [
                {"name": c['community_name'], "size": c['size'], "top_members": c['players'][:10]}
                for c in province_comms[:15]
            ],
            "multi_club_players": overlapping,
            "size_statistics": {
                "largest_club": club_comms[0] if club_comms else None,
                "largest_national": national_comms[0] if national_comms else None,
                "largest_province": province_comms[0] if province_comms else None
            }
        }
        
        self._log_community_results_native(community_results)
        self.results['community_detection'] = community_results
        return community_results
        
    def _log_community_results(self, results: Dict):
        """Log GDS community results."""
        logger.info(f"\n📊 Community Detection Results:")
        logger.info(f"   Total communities found: {results['total_communities']}")
        
        if results['communities']:
            logger.info(f"\n🏘️ Top 10 Largest Communities:")
            sorted_comms = sorted(
                results['communities'].items(),
                key=lambda x: -x[1]['size']
            )[:10]
            
            for comm_id, data in sorted_comms:
                logger.info(f"\n   Community {comm_id} ({data['size']} members):")
                logger.info(f"      Types: {', '.join(data['labels'])}")
                logger.info(f"      Members: {', '.join(data['members'][:5])}...")
                
    def _log_community_results_native(self, results: Dict):
        """Log native community results."""
        logger.info(f"\n📊 Community Detection Results:")
        logger.info(f"   • Club-based communities: {results['total_club_communities']}")
        logger.info(f"   • National team communities: {results['total_national_communities']}")
        logger.info(f"   • Province-based communities: {results['total_province_communities']}")
        
        # Top club communities
        logger.info(f"\n🏟️ Top 10 Club Communities (by player count):")
        for i, comm in enumerate(results['club_communities'][:10], 1):
            logger.info(f"   {i:2}. {comm['name'][:35]:35} - {comm['size']} players")
            
        # Top national team communities
        if results['national_communities']:
            logger.info(f"\n🏴 National Team Communities:")
            for i, comm in enumerate(results['national_communities'][:5], 1):
                logger.info(f"   {i}. {comm['name'][:35]:35} - {comm['size']} players")
                
        # Top province communities
        if results['province_communities']:
            logger.info(f"\n🗺️ Top Province Communities (by player origin):")
            for i, comm in enumerate(results['province_communities'][:10], 1):
                logger.info(f"   {i:2}. {comm['name'][:35]:35} - {comm['size']} players")
                
        # Players who played for multiple clubs
        if results['multi_club_players']:
            logger.info(f"\n🔄 Players with Most Club Connections:")
            for i, player in enumerate(results['multi_club_players'][:10], 1):
                clubs = ', '.join(player['clubs'][:5])
                logger.info(f"   {i:2}. {player['player'][:30]:30} - {len(player['clubs'])} clubs ({clubs}...)")
                
    def save_results(self, output_file: str = None):
        """Save analysis results to JSON file."""
        if output_file is None:
            output_file = REPORTS_DIR / "network_analysis_report.json"
        else:
            output_file = Path(output_file)
            
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
            
        logger.info(f"\n💾 Results saved to: {output_file}")
        return output_file
        
    def run_full_analysis(self):
        """Run complete network analysis pipeline."""
        logger.info("\n" + "="*70)
        logger.info("🚀 VIETNAM FOOTBALL NETWORK ANALYSIS")
        logger.info("="*70)
        
        # 1. Get basic statistics
        self.get_graph_statistics()
        
        # 2. Small World Analysis
        self.analyze_small_world()
        
        # 3. PageRank
        self.calculate_pagerank()
        
        # 4. Community Detection
        self.detect_communities()
        
        # Save results
        output_file = self.save_results()
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("📋 ANALYSIS SUMMARY")
        logger.info("="*70)
        
        sw = self.results.get('small_world', {})
        logger.info(f"\n🌍 Small World:")
        logger.info(f"   - Average Path Length: {sw.get('average_path_length', 'N/A')}")
        logger.info(f"   - Clustering Coefficient: {sw.get('clustering_coefficient', 'N/A')}")
        logger.info(f"   - Is Small World: {'Yes ✅' if sw.get('is_small_world') else 'No ❌'}")
        
        pr = self.results.get('pagerank', {})
        if pr.get('top_overall'):
            top = pr['top_overall'][0]
            logger.info(f"\n📊 Most Central Node: {top['name']} ({top['label']})")
            
        cd = self.results.get('community_detection', {})
        logger.info(f"\n👥 Communities Detected:")
        if 'total_communities' in cd:
            logger.info(f"   - Total: {cd['total_communities']}")
        else:
            logger.info(f"   - Club-based: {cd.get('total_club_communities', 0)}")
            logger.info(f"   - Province-based: {cd.get('total_province_communities', 0)}")
            
        logger.info("\n" + "="*70)
        logger.info("✅ Analysis Complete!")
        logger.info("="*70)
        
        return self.results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run social network analysis on Vietnam Football Knowledge Graph"
    )
    parser.add_argument(
        "--uri",
        default=NEO4J_URI,
        help="Neo4j URI"
    )
    parser.add_argument(
        "--user",
        default=NEO4J_USER,
        help="Neo4j username"
    )
    parser.add_argument(
        "--password",
        default=NEO4J_PASSWORD,
        help="Neo4j password"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path for results"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show graph statistics"
    )
    parser.add_argument(
        "--pagerank-only",
        action="store_true",
        help="Only run PageRank analysis"
    )
    parser.add_argument(
        "--community-only",
        action="store_true",
        help="Only run community detection"
    )
    parser.add_argument(
        "--small-world-only",
        action="store_true",
        help="Only run small world analysis"
    )
    
    args = parser.parse_args()
    
    analyzer = NetworkAnalyzer(args.uri, args.user, args.password)
    
    if not analyzer.connect():
        sys.exit(1)
        
    try:
        if args.stats_only:
            analyzer.get_graph_statistics()
        elif args.pagerank_only:
            analyzer.calculate_pagerank()
        elif args.community_only:
            analyzer.detect_communities()
        elif args.small_world_only:
            analyzer.analyze_small_world()
        else:
            analyzer.run_full_analysis()
            
        if args.output:
            analyzer.save_results(args.output)
            
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
