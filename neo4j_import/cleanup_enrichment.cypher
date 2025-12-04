// Cleanup script to remove unwanted nodes from enrichment
// Run this in Neo4j Browser or via cypher-shell

// 1. Delete all Entity nodes (generic unclassified entities)
MATCH (n:Entity)
DETACH DELETE n;

// 2. Delete all Position nodes (position should be a property of Player, not separate nodes)
MATCH (n:Position)
DETACH DELETE n;

// 3. Delete any DATE nodes if they exist
MATCH (n) WHERE n.name STARTS WITH 'ngày' AND n.created_by = 'enrichment'
DETACH DELETE n;

// 4. Show remaining enrichment nodes
MATCH (n) WHERE n.created_by = 'enrichment'
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC;
