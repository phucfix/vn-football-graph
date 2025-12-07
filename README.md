# Vietnam Football Knowledge Graph

A complete Python pipeline to create a knowledge graph of Vietnamese football players, coaches, clubs, and national teams from Wikipedia tiếng Việt, then import into Neo4j.

## 🎯 Project Overview

This project:
1. **Crawls** Vietnamese Wikipedia for football-related pages
2. **Parses** wikitext infoboxes to extract structured data
3. **Normalizes** and deduplicates entities
4. **Builds** relationships (teammates, coached-by, etc.)
5. **Imports** everything into Neo4j Aura

## 📊 Expected Data

| Entity Type | Expected Count |
|------------|----------------|
| Players | ~400-800 |
| Coaches | ~50-100 |
| Clubs | ~30-50 |
| National Teams | ~5-10 |
| Relationships | ~2000-5000 |

## 🗂️ Project Structure

```
vietnam-football-knowledge-graph/
├── config/
│   └── config.py                    # Configuration settings
├── scraper/
│   └── wikipedia_crawler.py         # Wikipedia page fetcher
├── parser/
│   └── infobox_parser.py            # Wikitext parser
├── processor/
│   ├── entity_builder.py            # Data normalization
│   └── relationship_builder.py      # Edge generation
├── neo4j_import/
│   ├── schema.cypher                # Neo4j constraints & indexes
│   ├── load_data.cypher             # LOAD CSV commands (reference)
│   └── import_to_neo4j.py           # Python import script
├── tools/
│   └── validation.py                # Graph validation
├── data/
│   ├── raw/                         # Raw JSON from Wikipedia
│   ├── parsed/                      # Parsed JSONL files
│   ├── processed/                   # Clean CSVs
│   └── edges/                       # Relationship CSVs
├── reports/
│   └── import_report.txt            # Validation report
├── requirements.txt
├── Makefile
├── run.sh
└── README.md

## 🤖 GraphRAG Chatbot
├── chatbot/
│   ├── README.md                    # Chatbot documentation
│   ├── config.py                    # Chatbot configuration
│   ├── knowledge_graph.py           # Neo4j interface
│   ├── multi_hop_reasoning.py       # Multi-hop reasoning engine
│   ├── chatbot.py                   # Main chatbot classes
│   ├── question_generator.py        # Evaluation question generator
│   ├── evaluator.py                 # Evaluation framework
│   └── evaluation/
│       ├── questions.json           # 2500 evaluation questions
│       └── results.json             # Evaluation results
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Neo4j Aura account (or local Neo4j)
- ~1GB disk space for data

### Installation

```bash
# Clone the repository
cd vietnam-football-knowledge-graph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set your Neo4j credentials as environment variables:

```bash
export NEO4J_URI="neo4j+s://xxxxxxxx.databases.neo4j.io"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
```

Or edit `config/config.py` directly.

### Run the Full Pipeline

```bash
# Using Make (recommended)
make all

# Or using the shell script
bash run.sh

# Or step by step
python -m scraper.wikipedia_crawler --fetch-all
python -m parser.infobox_parser --parse-all
python -m processor.entity_builder --normalize-all
python -m processor.relationship_builder --build-all
python -m neo4j_import.import_to_neo4j --uri $NEO4J_URI --user $NEO4J_USER --password $NEO4J_PASSWORD
python -m tools.validation --neo4j-uri $NEO4J_URI --user $NEO4J_USER --password $NEO4J_PASSWORD
```

## 📖 Step-by-Step Guide

### Step 1: Crawl Wikipedia

Fetch pages from Vietnamese Wikipedia categories:

```bash
# Fetch all categories
python -m scraper.wikipedia_crawler --fetch-all

# Fetch specific category
python -m scraper.wikipedia_crawler --category "Cầu thủ bóng đá Việt Nam" --entity-type player

# Re-fetch without cache
python -m scraper.wikipedia_crawler --fetch-all --no-cache
```

**Output:** `data/raw/*.json` files

### Step 2: Parse Infoboxes

Extract structured data from wikitext:

```bash
# Parse all entity types
python -m parser.infobox_parser --parse-all

# Parse specific type
python -m parser.infobox_parser --entity-type player
```

**Output:** `data/parsed/*.jsonl` files

### Step 3: Normalize Data

Clean and deduplicate entities:

```bash
python -m processor.entity_builder --normalize-all
```

**Output:** `data/processed/*.csv` files

### Step 4: Build Relationships

Generate edge tables:

```bash
python -m processor.relationship_builder --build-all
```

**Output:** `data/edges/*.csv` files

### Step 5: Import to Neo4j

Load data into Neo4j Aura:

```bash
# Fresh import
python -m neo4j_import.import_to_neo4j \
    --uri $NEO4J_URI \
    --user $NEO4J_USER \
    --password $NEO4J_PASSWORD

# Reset and reimport
python -m neo4j_import.import_to_neo4j \
    --uri $NEO4J_URI \
    --user $NEO4J_USER \
    --password $NEO4J_PASSWORD \
    --reset
```

### Step 6: Validate

Run validation queries:

```bash
python -m tools.validation \
    --neo4j-uri $NEO4J_URI \
    --user $NEO4J_USER \
    --password $NEO4J_PASSWORD
```

**Output:** `reports/import_report.txt`

## 🔍 Example Neo4j Queries

### Find a player's career

```cypher
MATCH (p:Player {name: "Nguyễn Công Phượng"})-[r:PLAYED_FOR]->(c:Club)
RETURN p.name, c.name, r.from_year, r.to_year, r.appearances, r.goals
ORDER BY r.from_year
```

### Find teammates

```cypher
MATCH (p1:Player {name: "Nguyễn Quang Hải"})-[:TEAMMATE]-(p2:Player)
RETURN p2.name, count(*) AS shared_clubs
ORDER BY shared_clubs DESC
```

### Players coached by a specific coach

```cypher
MATCH (c:Coach {name: "Park Hang-seo"})<-[:UNDER_COACH]-(p:Player)
RETURN p.name, p.position
```

### Position distribution

```cypher
MATCH (p:Player)-[:HAS_POSITION]->(pos:Position)
RETURN pos.position_name, count(p) AS player_count
ORDER BY player_count DESC
```

### Club with most players

```cypher
MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
RETURN c.name, count(DISTINCT p) AS total_players
ORDER BY total_players DESC
LIMIT 10
```

### Shortest path between two players

```cypher
MATCH path = shortestPath(
    (p1:Player {name: "Player A"})-[*]-(p2:Player {name: "Player B"})
)
RETURN path
```

## 📈 Data Model

### Nodes

| Label | Key Properties |
|-------|----------------|
| `Player` | wiki_id, name, position, nationality, date_of_birth |
| `Coach` | wiki_id, name, nationality |
| `Club` | wiki_id, name, founded, league |
| `NationalTeam` | wiki_id, name, level (senior/U23/etc.) |
| `Position` | position_id, position_code, position_name |
| `Nationality` | nationality_id, nationality_name, country_code |

### Relationships

| Type | From | To | Properties |
|------|------|-----|------------|
| `PLAYED_FOR` | Player | Club | from_year, to_year, appearances, goals |
| `PLAYED_FOR_NATIONAL` | Player | NationalTeam | from_year, to_year, appearances, goals |
| `COACHED` | Coach | Club | from_year, to_year, role |
| `COACHED_NATIONAL` | Coach | NationalTeam | from_year, to_year, role |
| `TEAMMATE` | Player | Player | club_name, from_year, to_year |
| `NATIONAL_TEAMMATE` | Player | Player | team_name, from_year, to_year |
| `UNDER_COACH` | Player | Coach | club_name, from_year, to_year |
| `HAS_POSITION` | Player | Position | - |
| `HAS_NATIONALITY` | Player/Coach | Nationality | - |

## 🔧 Troubleshooting

### "Connection failed" to Neo4j

- Check your URI format: `neo4j+s://` for Aura, `bolt://` for local
- Verify credentials
- Check if Aura instance is running

### "No pages found" during crawl

- Wikipedia category names might have changed
- Check `config/config.py` for category names
- Try listing categories: `python -m scraper.wikipedia_crawler --list-categories`

### "Parse error" for many pages

- Some pages don't have standard infoboxes
- ~80% success rate is normal
- Check `data/parsed/*.jsonl` for actual parsed data

### Import is slow

## 🤖 GraphRAG Chatbot

### Overview

Chatbot dựa trên đồ thị tri thức với:
- **Small LLM**: Qwen2-0.5B-Instruct (500M params)
- **GraphRAG**: Graph-based Retrieval Augmented Generation
- **Multi-hop Reasoning**: Hỗ trợ 1-hop, 2-hop, 3-hop queries
- **2500 câu hỏi đánh giá**: True/False, Yes/No, MCQ

### Quick Start

```bash
# Sử dụng chatbot
from chatbot import create_chatbot

bot = create_chatbot(use_llm=False)  # Graph-only mode
answer = bot.chat("Nguyễn Văn Quyết chơi cho đội nào?")
print(answer)
bot.close()
```

### Evaluation Results

| Metric | Value |
|--------|-------|
| **Overall Accuracy** | 76.80% |
| **MCQ Accuracy** | 95.79% |
| **Yes/No Accuracy** | 79.41% |
| **1-hop Accuracy** | 90.08% |

### Run Evaluation

```bash
# Generate questions (2500)
python -m chatbot.run_evaluation --generate

# Evaluate chatbot
python -m chatbot.run_evaluation --evaluate --max-questions 500
```

Xem chi tiết tại [chatbot/README.md](chatbot/README.md)

- Reduce batch size: `--batch-size 100`
- Aura free tier has rate limits
- Large teammate relationships take time

## 📝 License

MIT License

## 🙏 Acknowledgments

- Data source: [Vietnamese Wikipedia](https://vi.wikipedia.org)
- Built with: mwclient, mwparserfromhell, pandas, neo4j-python-driver
