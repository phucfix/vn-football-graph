// ============================================
// CLEANUP ENRICHMENT DATA FROM NEO4J
// Run this in Neo4j Browser step by step
// ============================================

// Step 1: Count enrichment data (run này trước để xem)
MATCH (n) WHERE n.created_by = "enrichment" 
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC;

// Step 2: Delete all edges connected to enrichment nodes
MATCH (n) WHERE n.created_by = "enrichment"
DETACH DELETE n;

// Step 3: Verify cleanup - should return 0
MATCH (n) WHERE n.created_by = "enrichment"
RETURN count(n) AS remaining_enrichment_nodes;

// Step 4: Check remaining data (original data)
MATCH (n) 
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC;
