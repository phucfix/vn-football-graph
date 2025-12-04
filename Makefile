.PHONY: all crawl parse normalize build-rels import validate clean help \
        enrich collect-texts preprocess-texts run-ner run-re validate-enrichment import-enriched enrich-report

# Load .env file if exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Default Neo4j settings (can be overridden)
NEO4J_URI ?= $(shell echo $$NEO4J_URI)
NEO4J_USER ?= neo4j
NEO4J_PASSWORD ?= $(shell echo $$NEO4J_PASSWORD)

# Python executable (use venv if available)
PYTHON := $(shell if [ -f .venv/bin/python ]; then echo ".venv/bin/python"; else echo "python"; fi)

help:
	@echo "Vietnam Football Knowledge Graph - Makefile"
	@echo ""
	@echo "=== ORIGINAL PIPELINE ==="
	@echo "  make all              Run the complete pipeline"
	@echo "  make crawl            Fetch pages from Wikipedia"
	@echo "  make parse            Parse wikitext infoboxes"
	@echo "  make normalize        Normalize and deduplicate entities"
	@echo "  make clean-players    Clean and filter Vietnamese players only"
	@echo "  make build-rels       Build relationship tables"
	@echo "  make import           Import data to Neo4j"
	@echo "  make validate         Validate the imported graph"
	@echo "  make clean            Remove all generated data"
	@echo ""
	@echo "=== ENRICHMENT PIPELINE (NLP) ==="
	@echo "  make enrich           Run complete enrichment pipeline"
	@echo "  make collect-texts    Collect Wikipedia article bodies"
	@echo "  make preprocess-texts Preprocess texts for NLP"
	@echo "  make run-ner          Run Named Entity Recognition"
	@echo "  make run-re           Run Relation Extraction"
	@echo "  make validate-enrichment  Validate extracted data"
	@echo "  make import-enriched  Import enriched data to Neo4j"
	@echo "  make import-enriched-dry  Preview enrichment (dry run)"
	@echo "  make enrich-report    Generate enrichment analytics"
	@echo "  make clean-enrichment Remove enrichment data"
	@echo ""
	@echo "=== SETUP ==="
	@echo "  make install          Install base dependencies"
	@echo "  make install-enrichment  Install NLP dependencies"
	@echo ""
	@echo "Environment variables:"
	@echo "  NEO4J_URI             Neo4j connection URI"
	@echo "  NEO4J_USER            Neo4j username (default: neo4j)"
	@echo "  NEO4J_PASSWORD        Neo4j password"

# Run complete pipeline
all: crawl parse normalize build-rels import validate
	@echo "Pipeline complete!"

# Step 1: Crawl Wikipedia
crawl:
	@echo "=== Step 1: Crawling Wikipedia ==="
	$(PYTHON) -m scraper.wikipedia_crawler --fetch-all

# Step 2: Parse infoboxes
parse:
	@echo "=== Step 2: Parsing Infoboxes ==="
	$(PYTHON) -m parser.infobox_parser --parse-all

# Step 3: Normalize entities
normalize:
	@echo "=== Step 3: Normalizing Entities ==="
	$(PYTHON) -m processor.entity_builder --normalize-all

# Step 3b: Clean Vietnamese players only
clean-players:
	@echo "=== Cleaning Vietnamese Players ==="
	$(PYTHON) -m processor.player_cleaner --update-main

# Step 4: Build relationships
build-rels:
	@echo "=== Step 4: Building Relationships ==="
	$(PYTHON) -m processor.relationship_builder --build-all

# Step 5: Import to Neo4j
import:
	@echo "=== Step 5: Importing to Neo4j ==="
	@if [ -z "$(NEO4J_URI)" ]; then \
		echo "Error: NEO4J_URI not set"; \
		exit 1; \
	fi
	@if [ -z "$(NEO4J_PASSWORD)" ]; then \
		echo "Error: NEO4J_PASSWORD not set"; \
		exit 1; \
	fi
	$(PYTHON) -m neo4j_import.import_to_neo4j \
		--uri "$(NEO4J_URI)" \
		--user "$(NEO4J_USER)" \
		--password "$(NEO4J_PASSWORD)"

# Step 5 (with reset): Import to Neo4j, deleting existing data first
import-reset:
	@echo "=== Step 5: Importing to Neo4j (with reset) ==="
	@if [ -z "$(NEO4J_URI)" ]; then \
		echo "Error: NEO4J_URI not set"; \
		exit 1; \
	fi
	$(PYTHON) -m neo4j_import.import_to_neo4j \
		--uri "$(NEO4J_URI)" \
		--user "$(NEO4J_USER)" \
		--password "$(NEO4J_PASSWORD)" \
		--reset

# Step 6: Validate
validate:
	@echo "=== Step 6: Validating Graph ==="
	@if [ -z "$(NEO4J_URI)" ]; then \
		echo "Error: NEO4J_URI not set"; \
		exit 1; \
	fi
	$(PYTHON) -m tools.validation \
		--neo4j-uri "$(NEO4J_URI)" \
		--user "$(NEO4J_USER)" \
		--password "$(NEO4J_PASSWORD)"

# Clean all generated data
clean:
	@echo "Cleaning generated data..."
	rm -rf data/raw/*.json
	rm -rf data/parsed/*.jsonl
	rm -rf data/processed/*.csv
	rm -rf data/edges/*.csv
	rm -rf reports/*.txt
	@echo "Clean complete!"

# Clean only processed data (keep raw)
clean-processed:
	@echo "Cleaning processed data..."
	rm -rf data/parsed/*.jsonl
	rm -rf data/processed/*.csv
	rm -rf data/edges/*.csv
	rm -rf reports/*.txt
	@echo "Clean complete!"

# Install dependencies
install:
	pip install -r requirements.txt

# Install enrichment dependencies (includes NLP libraries)
install-enrichment:
	pip install -r requirements_enrichment.txt

# Development: re-run from parsing onwards (skip crawl)
reprocess: parse normalize build-rels
	@echo "Reprocessing complete!"

# =============================================================================
# ENRICHMENT PIPELINE (NLP-based Knowledge Graph Enrichment)
# =============================================================================

# Run complete enrichment pipeline
enrich: collect-texts preprocess-texts run-ner run-re validate-enrichment import-enriched
	@echo "Enrichment pipeline complete!"

# Step E1: Collect text from Wikipedia article bodies
collect-texts:
	@echo "=== Enrichment Step 1: Collecting Text Sources ==="
	$(PYTHON) -m data_enrichment.text_collector --collect-wiki

# Step E2: Preprocess collected texts
preprocess-texts:
	@echo "=== Enrichment Step 2: Preprocessing Texts ==="
	$(PYTHON) -m data_enrichment.text_preprocessor --process-all

# Step E3: Run Named Entity Recognition
run-ner:
	@echo "=== Enrichment Step 3: Running NER ==="
	$(PYTHON) -m nlp.entity_recognizer --process-all

# Step E4: Run Relation Extraction
run-re:
	@echo "=== Enrichment Step 4: Running Relation Extraction ==="
	$(PYTHON) -m nlp.relation_extractor --process-all

# Step E5: Validate and deduplicate extracted data
validate-enrichment:
	@echo "=== Enrichment Step 5: Validating Extracted Data ==="
	$(PYTHON) -m enrichment.validation --validate-all
	$(PYTHON) -m enrichment.deduplication --deduplicate-all

# Step E6: Import enriched data to Neo4j
import-enriched:
	@echo "=== Enrichment Step 6: Importing Enriched Data ==="
	@if [ -z "$(NEO4J_URI)" ]; then \
		echo "Error: NEO4J_URI not set"; \
		exit 1; \
	fi
	NEO4J_URI="$(NEO4J_URI)" NEO4J_USER="$(NEO4J_USER)" NEO4J_PASSWORD="$(NEO4J_PASSWORD)" \
		$(PYTHON) -m neo4j_enrichment.enrich_graph --import-all --execute

# Step E6 (dry-run): Preview enrichment without importing
import-enriched-dry:
	@echo "=== Enrichment Step 6: Dry Run (Preview Only) ==="
	$(PYTHON) -m neo4j_enrichment.enrich_graph --import-all --dry-run

# Generate enrichment analytics report
enrich-report:
	@echo "=== Generating Enrichment Report ==="
	@if [ -z "$(NEO4J_URI)" ]; then \
		echo "Error: NEO4J_URI not set"; \
		exit 1; \
	fi
	$(PYTHON) -m tools.enrichment_analytics \
		--uri "$(NEO4J_URI)" \
		--user "$(NEO4J_USER)" \
		--password "$(NEO4J_PASSWORD)"

# Clean enrichment data only
clean-enrichment:
	@echo "Cleaning enrichment data..."
	rm -rf data/text_sources/*.json
	rm -rf data/processed_texts/*.jsonl
	rm -rf data/enrichment/*.jsonl
	rm -rf data/enrichment/*.csv
	rm -rf reports/enrichment_*.txt
	@echo "Enrichment data cleaned!"
