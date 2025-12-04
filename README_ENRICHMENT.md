# Vietnam Football Knowledge Graph - Enrichment Module

## 🎯 Overview

This module extends the Vietnam Football Knowledge Graph by extracting new entities and relationships from unstructured text sources using NLP techniques.

**Base Graph Statistics:**
- 526 Players
- 63 Coaches
- 78 Clubs
- 17 Edge Types

**Goal:** Discover implicit relationships and new facts that weren't captured in Wikipedia infoboxes.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install enrichment-specific dependencies
pip install -r requirements_enrichment.txt

# For GPU support on Arch Linux:
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### 2. Run the Pipeline

```bash
# Complete pipeline (recommended for first run)
make enrich

# Or step by step:
python -m data_enrichment.text_collector --collect-wiki
python -m data_enrichment.text_preprocessor --process-all
python -m nlp.entity_recognizer --process-all
python -m nlp.relation_extractor --process-all
python -m enrichment.validation --validate-all
python -m neo4j_enrichment.enrich_graph --import-all --dry-run
```

### 3. Check Results

```bash
# View analytics summary
python -m tools.enrichment_analytics --summary

# Generate full report
python -m tools.enrichment_analytics --full-report
```

## 📁 Project Structure

```
vn-football-graph/
├── config/
│   └── config_enrichment.yaml    # Enrichment configuration
├── data/
│   ├── text_sources/             # Collected texts
│   │   └── wikipedia/            # Wikipedia article bodies
│   ├── processed_texts/          # Preprocessed sentences
│   └── enrichment/               # NLP extraction outputs
│       ├── recognized_entities.jsonl
│       ├── extracted_relations.jsonl
│       └── validated_facts.jsonl
├── data_enrichment/              # Text collection module
│   ├── text_collector.py
│   └── text_preprocessor.py
├── nlp/                          # NLP pipeline
│   ├── entity_recognizer.py      # NER (PhoBERT + Dictionary)
│   └── relation_extractor.py     # RE (Pattern-based)
├── enrichment/                   # Validation module
│   ├── validation.py
│   └── deduplication.py
├── neo4j_enrichment/             # Graph import
│   └── enrich_graph.py
├── tools/
│   └── enrichment_analytics.py   # Analytics & reporting
├── docs/
│   └── nlp_pipeline.md          # Technical documentation
└── requirements_enrichment.txt   # Python dependencies
```

## 🔧 Pipeline Components

### 1. Text Collection
Extracts clean article text from Wikipedia pages (not just infoboxes).

```bash
# Collect all Wikipedia articles
python -m data_enrichment.text_collector --collect-wiki

# Collect specific entity type
python -m data_enrichment.text_collector --collect-wiki --entity-type player

# View statistics
python -m data_enrichment.text_collector --stats
```

### 2. Text Preprocessing
Normalizes Vietnamese text and segments into sentences.

```bash
# Process all collected texts
python -m data_enrichment.text_preprocessor --process-all

# Preview sentences from a file
python -m data_enrichment.text_preprocessor --preview player_526.txt
```

### 3. Named Entity Recognition (NER)
Recognizes football-related entities using hybrid approach:

- **Dictionary matching:** Links to existing KG entities
- **PhoBERT NER:** Recognizes unknown entities
- **Pattern matching:** Dates, positions, competitions

```bash
# Process all sentences
python -m nlp.entity_recognizer --process-all

# Test on single sentence
python -m nlp.entity_recognizer --sentence "Công Phượng ghi bàn cho HAGL tại V.League 2024"

# Use CPU only (no GPU)
python -m nlp.entity_recognizer --process-all --no-model
```

**Entity Types:**
| Type | Example |
|------|---------|
| PLAYER | Nguyễn Công Phượng |
| COACH | Park Hang-seo |
| CLUB | Hoàng Anh Gia Lai, HAGL |
| NATIONAL_TEAM | ĐTVN, U23 Việt Nam |
| STADIUM | Mỹ Đình |
| COMPETITION | V.League, AFF Cup |
| DATE | năm 2024, tháng 12 |

### 4. Relation Extraction (RE)
Extracts relationships using Vietnamese language patterns.

```bash
# Extract relations from recognized entities
python -m nlp.relation_extractor --process-all

# With custom confidence threshold
python -m nlp.relation_extractor --process-all --confidence-threshold 0.7
```

**Relation Types:**
| Type | Pattern Example | Meaning |
|------|-----------------|---------|
| PLAYED_FOR | "X chơi cho Y" | Player played for club |
| COACHED | "X dẫn dắt Y" | Coach coached team |
| TRANSFERRED_TO | "X chuyển đến Y" | Player transferred |
| SCORED_IN | "X ghi bàn cho Y" | Player scored |
| DEFEATED | "X thắng Y" | Team defeated team |

### 5. Validation & Deduplication
Validates extracted data against existing KG.

```bash
# Validate all
python -m enrichment.validation --validate-all

# Generate report
python -m enrichment.validation --generate-report
```

### 6. Neo4j Import
Imports validated data into the knowledge graph.

```bash
# Preview changes (dry run)
python -m neo4j_enrichment.enrich_graph --import-all --dry-run

# Execute import
python -m neo4j_enrichment.enrich_graph --import-all --execute

# Generate Cypher scripts for manual import
python -m neo4j_enrichment.enrich_graph --generate-scripts
```

## 📊 Example Output

### Recognized Entities
```json
{
  "sentence": "Nguyễn Công Phượng ghi bàn cho Sài Gòn FC tại Mỹ Đình",
  "entities": [
    {"text": "Nguyễn Công Phượng", "type": "PLAYER", "wiki_id": 526, "confidence": 0.98},
    {"text": "Sài Gòn FC", "type": "CLUB", "wiki_id": 12, "confidence": 0.95},
    {"text": "Mỹ Đình", "type": "STADIUM", "wiki_id": 8, "confidence": 0.99}
  ]
}
```

### Extracted Relations
```json
{
  "sentence": "Nguyễn Công Phượng ghi bàn cho Sài Gòn FC",
  "relations": [
    {
      "subject": {"text": "Nguyễn Công Phượng", "type": "PLAYER"},
      "predicate": "SCORED_IN",
      "object": {"text": "Sài Gòn FC", "type": "CLUB"},
      "confidence": 0.87
    }
  ]
}
```

## ⚙️ Configuration

Edit `config/config_enrichment.yaml`:

```yaml
# NLP settings
nlp:
  ner:
    model_type: "hybrid"  # "phobert", "dictionary", "hybrid"
    phobert:
      device: "auto"      # "auto", "cuda", "cpu"
      batch_size: 16      # Reduce if OOM

# Confidence thresholds
confidence:
  auto_import:
    entity: 0.85
    relation: 0.75
  discard:
    entity: 0.50
```

## 📈 Analytics

```bash
# Print summary
python -m tools.enrichment_analytics --summary

# Show growth statistics
python -m tools.enrichment_analytics --show-growth

# Quality metrics
python -m tools.enrichment_analytics --quality-metrics
```

### Expected Results

| Metric | Baseline | After Enrichment |
|--------|----------|------------------|
| Players | 526 | 580-620 |
| Coaches | 63 | 75-85 |
| Clubs | 78 | 90-110 |
| Edge Types | 17 | 22-25 |
| Total Edges | ~2000 | ~3500-4500 |

## 🔍 Troubleshooting

### CUDA/GPU Issues
```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Force CPU mode
python -m nlp.entity_recognizer --device cpu
```

### Memory Issues
Reduce batch size in config:
```yaml
nlp:
  ner:
    phobert:
      batch_size: 8
```

### Missing underthesea
```bash
pip install underthesea
```

## 📚 Documentation

- **Technical Details:** [docs/nlp_pipeline.md](docs/nlp_pipeline.md)
- **Configuration:** [config/config_enrichment.yaml](config/config_enrichment.yaml)

## 🤝 Contributing

1. Run on small batch first (100 texts)
2. Check quality metrics before full run
3. Always use `--dry-run` before importing to Neo4j
4. Tag all enriched data with source="text_extraction"

## 📝 License

MIT License - See base project for details.
