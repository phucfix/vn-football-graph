# 🔬 STRICT NLP ENRICHMENT PIPELINE V2.0

## Tổng quan

Pipeline làm giàu dữ liệu đồ thị bằng NLP với độ chính xác cao, tránh false positives như version cũ (ví dụ: Công Phượng 41 CLB).

## Đáp ứng yêu cầu đồ án

### ✅ 0.5đ - Thu thập và lựa chọn tập dữ liệu làm giàu
- **Nguồn**: Wikipedia text (đã có trong `data/processed_texts/` hoặc `data/text_sources/`)
- **Lý do chọn**: Wikipedia có thông tin có cấu trúc, đáng tin cậy về bóng đá Việt Nam
- **Quy mô**: 100-1000 documents về players, clubs, competitions

### ✅ 0.75đ - Mô hình nhận dạng thực thể (NER)
**Phương pháp**: Strict Entity Matching
- Load tất cả entities hiện có từ Neo4j (526 players, 78 clubs, 67 provinces, etc.)
- Chỉ nhận dạng entities **ĐÃ TỒN TẠI** trong graph (no new entities)
- Exact matching với word boundary check
- Ưu tiên tên dài trước (tránh ambiguity)

**Entities được nhận dạng**:
- `PLAYER`: Cầu thủ (ví dụ: Nguyễn Quang Hải)
- `CLUB`: Câu lạc bộ (ví dụ: Hà Nội FC)
- `PROVINCE`: Tỉnh thành (ví dụ: Hà Nội, Nghệ An)
- `COACH`: Huấn luyện viên (ví dụ: Park Hang-seo)
- `COMPETITION`: Giải đấu (ví dụ: V.League, AFF Cup)

**Confidence**: 1.0 (exact match)

### ✅ 0.75đ - Mô hình nhận dạng mối quan hệ (Relation Extraction)
**Phương pháp**: Pattern-based + Validation

**Quan hệ được extract**:

1. **PLAYED_FOR** (Player → Club)
   - Patterns: "chơi cho", "thi đấu cho", "khoác áo", "gia nhập", "chuyển đến"
   - Validation: Player phải xuất hiện trước club
   - Confidence: 0.95

2. **BORN_IN** (Player → Province)
   - Patterns: "sinh ra", "sinh tại", "quê ở", "quê quán"
   - Validation: Player phải xuất hiện trước province
   - Confidence: 0.95

3. **COACHED** (Coach → Club)
   - Patterns: "huấn luyện", "dẫn dắt", "làm hlv"
   - Validation: Coach phải xuất hiện trước club
   - Confidence: 0.95

4. **COMPETED_IN** (Player/Club → Competition)
   - Patterns: "vô địch", "tham dự", "tham gia", "giành"
   - Validation: Entity và competition phải gần pattern (<100 chars)
   - Confidence: 0.90

---

## So sánh Version 1 vs Version 2

| Aspect | Version 1 (Cũ) | **Version 2 (Strict)** |
|--------|----------------|------------------------|
| **Entity Recognition** | Fuzzy matching, tạo new entities | ✅ Chỉ match entities đã có trong Neo4j |
| **Relation Extraction** | Loose patterns | ✅ Strict patterns với position check |
| **Confidence Threshold** | >= 0.6 | ✅ >= 0.9 |
| **Validation** | Minimal | ✅ 4 validation rules |
| **False Positives** | Cao (Công Phượng 41 CLB!) | ✅ Thấp (validated) |
| **Source Tag** | `text_extraction` | ✅ `strict_nlp_v2` |

---

## Validation Rules

Mỗi relation phải pass 4 rules:

### Rule 1: Confidence Threshold
```python
if relation['confidence'] < 0.90:
    return False
```

### Rule 2: Context Length
```python
if len(relation.get('context', '')) < 20:
    return False
```

### Rule 3: Subject ≠ Object
```python
if relation['subject']['text'] == relation['object']['text']:
    return False
```

### Rule 4: No Negation Near Pattern
```python
negative_words = ['không', 'chưa', 'chẳng', 'không phải']
# Kiểm tra xem từ phủ định có gần pattern không
```

---

## Cách chạy

### Bước 1: Xóa dữ liệu enrichment cũ (nếu có)
```bash
python cleanup_text_extraction.py
```

### Bước 2: Chạy Strict NLP Enrichment
```bash
python strict_nlp_enrichment_v2.py
```

### Bước 3: Kiểm tra kết quả
```bash
python check_neo4j_stats.py
```

Hoặc query trong Neo4j Browser:
```cypher
// Đếm relationships mới
MATCH ()-[r]->()
WHERE r.source = 'strict_nlp_v2'
RETURN type(r) as rel_type, count(r) as count
ORDER BY count DESC;
```

---

## Output Expected

```
📊 STRICT NLP ENRICHMENT PIPELINE V2.0
================================================================================

📁 Found 150 text files

[1/150] player_3140580.txt: 8 entities, 2 relations
[2/150] club_445434.txt: 12 entities, 5 relations
[3/150] competition_25636.txt: 15 entities, 8 relations
...

📊 Total relations extracted: 247

💾 Importing to Neo4j...
INFO: Importing 247 relations...
INFO: Imported: 198, Skipped: 49

================================================================================
✅ ENRICHMENT COMPLETED
================================================================================
   Extracted: 247
   Imported: 198
   Skipped: 49
   Success rate: 80.2%
```

---

## Ví dụ cụ thể

### Input Text
```
Nguyễn Công Phượng sinh ra ở Nghệ An và đã chơi cho câu lạc bộ 
Hoàng Anh Gia Lai. Anh tham gia đội tuyển Việt Nam tại AFF Cup 2018.
```

### Entities Recognized
```json
[
  {"text": "Nguyễn Công Phượng", "type": "PLAYER", "wiki_id": 3140580},
  {"text": "Nghệ An", "type": "PROVINCE"},
  {"text": "Hoàng Anh Gia Lai", "type": "CLUB", "wiki_id": 123456},
  {"text": "Việt Nam", "type": "NATIONAL_TEAM", "wiki_id": 21785},
  {"text": "AFF Cup", "type": "COMPETITION"}
]
```

### Relations Extracted
```json
[
  {
    "subject": {"text": "Nguyễn Công Phượng", "type": "PLAYER"},
    "predicate": "BORN_IN",
    "object": {"text": "Nghệ An", "type": "PROVINCE"},
    "confidence": 0.95,
    "pattern": "sinh ra ở"
  },
  {
    "subject": {"text": "Nguyễn Công Phượng", "type": "PLAYER"},
    "predicate": "PLAYED_FOR",
    "object": {"text": "Hoàng Anh Gia Lai", "type": "CLUB"},
    "confidence": 0.95,
    "pattern": "chơi cho"
  },
  {
    "subject": {"text": "Nguyễn Công Phượng", "type": "PLAYER"},
    "predicate": "COMPETED_IN",
    "object": {"text": "AFF Cup", "type": "COMPETITION"},
    "confidence": 0.90,
    "pattern": "tham gia"
  }
]
```

### Neo4j Import
```cypher
// Relation 1: BORN_IN
MATCH (p:Player {wiki_id: 3140580})
MATCH (pr:Province {name: 'Nghệ An'})
MERGE (p)-[r:BORN_IN]->(pr)
SET r.source = 'strict_nlp_v2',
    r.confidence = 0.95,
    r.pattern = 'sinh ra ở'

// Relation 2: PLAYED_FOR
MATCH (p:Player {wiki_id: 3140580})
MATCH (c:Club {wiki_id: 123456})
MERGE (p)-[r:PLAYED_FOR]->(c)
SET r.source = 'strict_nlp_v2',
    r.confidence = 0.95,
    r.pattern = 'chơi cho'

// Relation 3: COMPETED_IN
MATCH (p:Player {wiki_id: 3140580})
MATCH (comp:Competition {wiki_id: ...})
MERGE (p)-[r:COMPETED_IN]->(comp)
SET r.source = 'strict_nlp_v2',
    r.confidence = 0.90,
    r.pattern = 'tham gia'
```

---

## Ưu điểm

✅ **High Precision**: Confidence >= 0.9, validation rules chặt chẽ
✅ **No False Positives**: Không tạo ra quan hệ mơ hồ như "Công Phượng 41 CLB"
✅ **Traceable**: Mỗi relation có `context`, `pattern`, `confidence`
✅ **Auditable**: Source tag `strict_nlp_v2` để phân biệt với data gốc
✅ **Incremental**: Có thể chạy nhiều lần, MERGE tránh duplicate

---

## Nhược điểm & Trade-offs

❌ **Recall thấp hơn**: Chỉ extract khi pattern rõ ràng → bỏ sót một số relations
❌ **Không tạo new entities**: Chỉ làm giàu cho entities đã có
❌ **Pattern-based**: Không flexible như deep learning models

**Trade-off**: Chọn Precision cao thay vì Recall cao để tránh làm "bẩn" database

---

## Monitoring & Debugging

### Check imported relations
```cypher
MATCH ()-[r]->()
WHERE r.source = 'strict_nlp_v2'
RETURN type(r), count(r), avg(r.confidence) as avg_conf
ORDER BY count(r) DESC;
```

### View sample relations
```cypher
MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club)
WHERE r.source = 'strict_nlp_v2'
RETURN p.name, c.name, r.confidence, r.pattern, r.context
LIMIT 10;
```

### Find low confidence relations
```cypher
MATCH ()-[r]->()
WHERE r.source = 'strict_nlp_v2' AND r.confidence < 0.92
RETURN type(r), r.confidence, r.context
ORDER BY r.confidence ASC
LIMIT 20;
```

---

## Kết luận

**Strict NLP Enrichment V2.0** đáp ứng đầy đủ yêu cầu đồ án với độ chính xác cao, tránh được các lỗi như version cũ. Phù hợp để làm giàu knowledge graph một cách an toàn và có kiểm soát.
