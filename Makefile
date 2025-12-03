.PHONY: all crawl parse normalize build-rels import validate clean help

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
	@echo "Usage:"
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

# Development: re-run from parsing onwards (skip crawl)
reprocess: parse normalize build-rels
	@echo "Reprocessing complete!""
