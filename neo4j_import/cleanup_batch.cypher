// ============================================
// CLEANUP ENRICHMENT DATA - BATCH DELETE
// Run each command ONE BY ONE in Neo4j Browser
// Wait for each to complete before running next
// ============================================

// Step 1: Check how many nodes to delete
MATCH (n) WHERE n.created_by = "enrichment"
RETURN count(n) AS total_enrichment_nodes;

// Step 2: Delete in batches of 1000 (run multiple times until 0 deleted)
// Copy and paste this, run it repeatedly until "deleted: 0"

MATCH (n) WHERE n.created_by = "enrichment"
WITH n LIMIT 1000
DETACH DELETE n
RETURN count(*) AS deleted;

// Keep running Step 2 until it returns 0

// Step 3: Verify cleanup complete
MATCH (n) WHERE n.created_by = "enrichment"
RETURN count(n) AS remaining;

// Step 4: Check final node counts
MATCH (n)
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC;
