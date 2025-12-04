# Vietnam Football Knowledge Graph - NLP Enrichment Pipeline

## Overview

This document describes the NLP pipeline used for enriching the Vietnam Football Knowledge Graph with new entities and relationships extracted from unstructured text sources.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NLP ENRICHMENT PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Wikipedia  │    │    Text      │    │  Sentence    │                  │
│  │   Articles   │───▶│  Collector   │───▶│ Preprocessor │                  │
│  │   (Raw)      │    │              │    │              │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                 │                           │
│                                                 ▼                           │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                    NLP PROCESSING                                   │   │
│  │  ┌─────────────────┐         ┌─────────────────────┐              │   │
│  │  │  Dictionary     │         │    Relation         │              │   │
│  │  │  Matching       │         │    Extractor        │              │   │
│  │  │  (Existing KG)  │         │    (Pattern-based)  │              │   │
│  │  └────────┬────────┘         └──────────┬──────────┘              │   │
│  │           │                              │                         │   │
│  │           ▼                              │                         │   │
│  │  ┌─────────────────┐                    │                         │   │
│  │  │  PhoBERT NER    │◀───────────────────┘                         │   │
│  │  │  (Vietnamese)   │                                              │   │
│  │  └────────┬────────┘                                              │   │
│  │           │                                                        │   │
│  └───────────┼────────────────────────────────────────────────────────┘   │
│              ▼                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      VALIDATION & IMPORT                              │ │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │ │
│  │  │   Entity     │    │   Relation   │    │   Neo4j      │           │ │
│  │  │   Linking    │───▶│   Validation │───▶│   Import     │           │ │
│  │  │              │    │              │    │              │           │ │
│  │  └──────────────┘    └──────────────┘    └──────────────┘           │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Text Collection (`data_enrichment/`)

**text_collector.py**
- Extracts article body text from Wikipedia (not just infobox)
- Cleans wiki markup, templates, citations
- Caches raw texts for reproducibility

**text_preprocessor.py**
- Vietnamese Unicode normalization (NFC)
- Sentence segmentation using `underthesea`
- Token cleaning and noise removal

### 2. Named Entity Recognition (`nlp/entity_recognizer.py`)

**Hybrid NER Approach:**

| Method | Use Case | Confidence |
|--------|----------|------------|
| Dictionary Matching | Known entities from KG | 1.0 (exact), 0.85+ (fuzzy) |
| PhoBERT NER | Unknown entities | 0.5-0.9 |
| Pattern Matching | Dates, positions, competitions | 0.9-0.95 |

**Entity Types:**
- `PLAYER` - Vietnamese football players
- `COACH` - Coaches and managers
- `CLUB` - Football clubs
- `NATIONAL_TEAM` - National teams (ĐTVN, U23, etc.)
- `STADIUM` - Stadiums and venues
- `PROVINCE` - Vietnamese provinces
- `COMPETITION` - Tournaments and leagues
- `EVENT` - Specific matches or events
- `DATE` - Dates in Vietnamese format
- `POSITION` - Player positions

### 3. Relation Extraction (`nlp/relation_extractor.py`)

**Pattern-Based RE:**

Vietnamese patterns for common football relationships:

```python
# PLAYED_FOR
"X chơi cho Y"         → PLAYED_FOR(X, Y)
"X khoác áo Y"         → PLAYED_FOR(X, Y)
"X thi đấu cho Y"      → PLAYED_FOR(X, Y)

# COACHED
"HLV X dẫn dắt Y"      → COACHED(X, Y)
"X làm HLV Y"          → COACHED(X, Y)

# TRANSFERRED_TO
"X chuyển đến Y"       → TRANSFERRED_TO(X, Y)
"X gia nhập Y"         → TRANSFERRED_TO(X, Y)

# SCORED_IN
"X ghi bàn cho Y"      → SCORED_IN(X, Y)
"bàn thắng của X vào lưới Y" → SCORED_IN(X, Y)

# DEFEATED
"X thắng Y"            → DEFEATED(X, Y)
"X đánh bại Y"         → DEFEATED(X, Y)
```

**Relation Types:**
- `PLAYED_FOR` - Player played for club/national team
- `COACHED` - Coach coached team
- `TRANSFERRED_TO` - Player transferred to club
- `SCORED_IN` - Player scored in match/competition
- `DEFEATED` - Team defeated another team
- `COMPETED_IN` - Entity competed in competition
- `PLAYS_AT` - Club plays at stadium
- `BORN_IN` - Person born in location
- `CAPTAINED` - Player captained team
- `WON_AWARD` - Person won award

### 4. Validation (`enrichment/validation.py`)

**Deduplication:**
- Fuzzy string matching against existing KG entities
- Threshold: 0.90 for entity matching

**Consistency Checks:**
- Temporal consistency (date conflicts)
- Type constraints (relation argument types)
- Graph structure validation

**Conflict Resolution:**
- Prefer infobox data over text extraction
- Keep both versions when in conflict, flag for review

### 5. Neo4j Import (`neo4j_enrichment/enrich_graph.py`)

**Import Strategy:**
- Dry-run mode for preview
- Batch imports with transaction safety
- Source tagging for provenance

**Source Weights:**
| Source | Weight |
|--------|--------|
| Infobox (structured) | 1.0 |
| Wikipedia body | 0.85 |
| News articles | 0.70 |

## Models Used

### PhoBERT (VinAI)
- **Model:** `vinai/phobert-base`
- **Purpose:** Vietnamese NER
- **Source:** [VinAI Research](https://github.com/VinAIResearch/PhoBERT)

### Vietnamese NER
- **Model:** `NlpHUST/ner-vietnamese-electra-base`
- **Purpose:** Named entity recognition for Vietnamese

### Sentence Embeddings
- **Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Purpose:** Semantic similarity for entity linking

## Configuration

See `config/config_enrichment.yaml` for full configuration options.

**Key Thresholds:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ner.dictionary.fuzzy_threshold` | 0.85 | Min similarity for fuzzy entity matching |
| `confidence.auto_import.entity` | 0.85 | Auto-import threshold for entities |
| `confidence.auto_import.relation` | 0.75 | Auto-import threshold for relations |
| `confidence.discard.entity` | 0.50 | Discard threshold for entities |

## Usage

### Full Pipeline

```bash
# 1. Collect Wikipedia article texts
python -m data_enrichment.text_collector --collect-wiki

# 2. Preprocess texts into sentences
python -m data_enrichment.text_preprocessor --process-all

# 3. Run NER on sentences
python -m nlp.entity_recognizer --process-all

# 4. Extract relations
python -m nlp.relation_extractor --process-all

# 5. Validate extracted data
python -m enrichment.validation --validate-all

# 6. Import to Neo4j (dry-run first)
python -m neo4j_enrichment.enrich_graph --import-all --dry-run

# 7. Execute import
python -m neo4j_enrichment.enrich_graph --import-all --execute
```

### Individual Steps

```bash
# Test NER on single sentence
python -m nlp.entity_recognizer --sentence "Công Phượng ghi bàn cho HAGL"

# Check analytics
python -m tools.enrichment_analytics --summary
```

## Output Files

| File | Description |
|------|-------------|
| `data/text_sources/wikipedia/*.txt` | Collected article texts |
| `data/processed_texts/*_sentences.jsonl` | Preprocessed sentences |
| `data/enrichment/recognized_entities.jsonl` | NER results |
| `data/enrichment/extracted_relations.jsonl` | RE results |
| `data/enrichment/validated_*.jsonl` | Validated data |
| `reports/enrichment_*.json` | Reports and analytics |

## Performance

### Expected Results (526 players baseline):

| Metric | Target |
|--------|--------|
| Entity recognition precision | ≥ 80% |
| Relation extraction precision | ≥ 70% |
| New entities discovered | 50-100 |
| New relations discovered | 500-1000 |

## Troubleshooting

### GPU Issues
If PhoBERT runs slowly or crashes:
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Force CPU mode
python -m nlp.entity_recognizer --device cpu
```

### Memory Issues
Reduce batch size in `config_enrichment.yaml`:
```yaml
nlp:
  ner:
    phobert:
      batch_size: 8  # Reduce from 16
```

### Missing Dependencies
```bash
pip install -r requirements_enrichment.txt
```
