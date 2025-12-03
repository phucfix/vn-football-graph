#!/bin/bash
# Vietnam Football Knowledge Graph - Pipeline Runner
# Usage: bash run.sh [--reset]

set -e  # Exit on error

echo "========================================"
echo "Vietnam Football Knowledge Graph Pipeline"
echo "========================================"
echo ""

# Check for required environment variables
if [ -z "$NEO4J_URI" ]; then
    echo "Warning: NEO4J_URI not set. Neo4j import will be skipped."
    echo "Set it with: export NEO4J_URI='neo4j+s://xxx.databases.neo4j.io'"
    SKIP_NEO4J=true
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    echo "Warning: NEO4J_PASSWORD not set. Neo4j import will be skipped."
    echo "Set it with: export NEO4J_PASSWORD='your-password'"
    SKIP_NEO4J=true
fi

NEO4J_USER="${NEO4J_USER:-neo4j}"

# Parse arguments
RESET_FLAG=""
if [ "$1" = "--reset" ]; then
    RESET_FLAG="--reset"
    echo "Reset mode enabled - existing Neo4j data will be deleted"
fi

echo ""

# Step 1: Crawl Wikipedia
echo "========================================"
echo "Step 1/6: Crawling Wikipedia"
echo "========================================"
python -m scraper.wikipedia_crawler --fetch-all
echo "✓ Crawling complete"
echo ""

# Step 2: Parse Infoboxes
echo "========================================"
echo "Step 2/6: Parsing Infoboxes"
echo "========================================"
python -m parser.infobox_parser --parse-all
echo "✓ Parsing complete"
echo ""

# Step 3: Normalize Entities
echo "========================================"
echo "Step 3/6: Normalizing Entities"
echo "========================================"
python -m processor.entity_builder --normalize-all
echo "✓ Normalization complete"
echo ""

# Step 4: Build Relationships
echo "========================================"
echo "Step 4/6: Building Relationships"
echo "========================================"
python -m processor.relationship_builder --build-all
echo "✓ Relationship building complete"
echo ""

# Step 5: Import to Neo4j
if [ "$SKIP_NEO4J" = true ]; then
    echo "========================================"
    echo "Step 5/6: Skipping Neo4j Import"
    echo "========================================"
    echo "Set NEO4J_URI and NEO4J_PASSWORD to enable import"
else
    echo "========================================"
    echo "Step 5/6: Importing to Neo4j"
    echo "========================================"
    python -m neo4j_import.import_to_neo4j \
        --uri "$NEO4J_URI" \
        --user "$NEO4J_USER" \
        --password "$NEO4J_PASSWORD" \
        $RESET_FLAG
    echo "✓ Neo4j import complete"
fi
echo ""

# Step 6: Validate
if [ "$SKIP_NEO4J" = true ]; then
    echo "========================================"
    echo "Step 6/6: Skipping Validation"
    echo "========================================"
    echo "Neo4j not configured, skipping validation"
else
    echo "========================================"
    echo "Step 6/6: Validating Graph"
    echo "========================================"
    python -m tools.validation \
        --neo4j-uri "$NEO4J_URI" \
        --user "$NEO4J_USER" \
        --password "$NEO4J_PASSWORD"
    echo "✓ Validation complete"
fi
echo ""

echo "========================================"
echo "Pipeline Complete!"
echo "========================================"
echo ""
echo "Generated files:"
echo "  - data/raw/*.json          (raw Wikipedia pages)"
echo "  - data/parsed/*.jsonl      (parsed entities)"
echo "  - data/processed/*.csv     (clean entities)"
echo "  - data/edges/*.csv         (relationships)"
echo "  - reports/import_report.txt (validation report)"
echo ""

if [ "$SKIP_NEO4J" != true ]; then
    echo "Your knowledge graph is now available in Neo4j!"
    echo "Connect to: $NEO4J_URI"
fi
