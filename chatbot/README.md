# 🤖 Vietnam Football Knowledge Graph Chatbot

Hệ thống Chatbot dựa trên Đồ thị Tri thức Bóng đá Việt Nam sử dụng GraphRAG và Multi-hop Reasoning.

## 📋 Tổng quan

### Yêu cầu đã thực hiện
- ✅ **Small LLM (≤1B params)**: Hỗ trợ Qwen2-0.5B-Instruct (500M params)
- ✅ **GraphRAG**: Graph-based Retrieval Augmented Generation
- ✅ **Multi-hop Reasoning**: Suy luận đa bước (1-hop, 2-hop, 3-hop)
- ✅ **2000+ câu hỏi đánh giá**: 2500 câu hỏi (T/F, Yes/No, MCQ)
- ✅ **So sánh với chatbot phổ biến**: Framework đánh giá với external APIs

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Question                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Entity Extraction                             │
│            (String matching + Graph search)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Knowledge Graph (Neo4j)                          │
│   - 1,060 nodes (Players, Clubs, Provinces, etc.)               │
│   - 39,114 relationships (PLAYED_FOR, TEAMMATE, etc.)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Multi-hop Reasoning                             │
│   - Path finding (1-3 hops)                                     │
│   - Relationship aggregation                                     │
│   - Evidence collection                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Answer Generation                             │
│   - SimpleChatbot: Graph-only (fast)                            │
│   - GraphRAGChatbot: Graph + LLM (accurate)                     │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Cấu trúc Module

```
chatbot/
├── __init__.py              # Module exports
├── config.py                # Cấu hình (Neo4j, LLM, etc.)
├── knowledge_graph.py       # Interface đồ thị Neo4j
├── multi_hop_reasoning.py   # Multi-hop reasoning engine
├── chatbot.py               # GraphRAGChatbot & SimpleChatbot
├── question_generator.py    # Tạo câu hỏi đánh giá
├── evaluator.py             # Framework đánh giá
├── run_evaluation.py        # Script chạy đánh giá
├── EVALUATION_REPORT.md     # Báo cáo kết quả
└── evaluation/
    ├── questions.json       # 2500 câu hỏi đánh giá
    └── results.json         # Kết quả đánh giá
```

## 🚀 Hướng dẫn Sử dụng

### 1. Cài đặt dependencies

```bash
pip install neo4j transformers torch tqdm python-dotenv
```

### 2. Cấu hình môi trường

Tạo file `.env`:
```
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. Sử dụng Chatbot

```python
from chatbot import create_chatbot

# Sử dụng SimpleChatbot (nhanh, chỉ dựa trên graph)
bot = create_chatbot(use_llm=False)

# Hỏi đáp
response = bot.chat("Nguyễn Văn Quyết chơi cho đội nào?")
print(response)

# Trả lời Yes/No
answer, confidence = bot.answer_yes_no("Nguyễn Văn Quyết từng chơi cho Hà Nội?")
print(f"Answer: {answer} (confidence: {confidence})")

# Trả lời MCQ
answer, conf, explanation = bot.answer_mcq(
    "Nguyễn Văn Quyết sinh ra ở đâu?",
    ["Hà Nội", "Nghệ An", "Hải Phòng", "Đà Nẵng"]
)
print(f"Answer: {answer}")

bot.close()
```

### 4. Chạy Đánh giá

```bash
# Tạo câu hỏi đánh giá (nếu chưa có)
python -m chatbot.run_evaluation --generate

# Chạy đánh giá (500 câu đầu)
python -m chatbot.run_evaluation --evaluate --max-questions 500

# Chạy đầy đủ 2500 câu
python -m chatbot.run_evaluation --evaluate
```

## 📊 Kết quả Đánh giá

### Overall Performance

| Metric | Value |
|--------|-------|
| **Accuracy** | 76.80% |
| **Avg Confidence** | 80.07% |
| **Avg Response Time** | 3.57s |

### By Question Type

| Type | Accuracy | Questions |
|------|----------|-----------|
| True/False | 58.17% | 1000 |
| Yes/No | 79.41% | 500 |
| MCQ | **95.79%** | 1000 |

### By Hop Level

| Level | Accuracy | Complexity |
|-------|----------|------------|
| 1-hop | **90.08%** | Direct relations |
| 2-hop | 37.18% | 1 intermediate |
| 3-hop | 38.78% | 2 intermediates |

## 🔧 Cấu hình

### config.py

```python
# Language Model
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"  # 500M params
MODEL_MAX_LENGTH = 512
MODEL_TEMPERATURE = 0.3

# Knowledge Graph
MAX_HOPS = 3
MAX_PATHS = 5

# Evaluation
EVALUATION_BATCH_SIZE = 50
```

## 📈 Cải thiện Dự kiến

1. **Hybrid LLM+Graph**: Kết hợp reasoning với generation
2. **Better Entity Extraction**: NER model thay string matching
3. **Multi-hop Caching**: Cache paths cho queries lặp lại
4. **Confidence Calibration**: Điều chỉnh confidence scores

## 📝 API Reference

### SimpleChatbot

```python
class SimpleChatbot:
    def initialize() -> bool
    def chat(question: str) -> str
    def answer_yes_no(question: str) -> Tuple[str, float]
    def answer_mcq(question: str, choices: List[str]) -> Tuple[str, float, str]
    def close()
```

### GraphRAGChatbot

```python
class GraphRAGChatbot:
    def initialize() -> bool
    def chat(question: str) -> ChatResponse
    def answer_yes_no(question: str) -> Tuple[str, float, str]
    def answer_mcq(question: str, choices: List[str]) -> Tuple[str, float, str]
    def close()
```

### KnowledgeGraph

```python
class KnowledgeGraph:
    def connect() -> bool
    def search_entities(query: str, limit: int) -> List[Entity]
    def get_entity_relationships(name: str) -> List[Relationship]
    def find_path(source: str, target: str, max_hops: int) -> Path
    def execute_cypher(query: str, params: Dict) -> List[Dict]
    def close()
```

## 📄 License

MIT License
