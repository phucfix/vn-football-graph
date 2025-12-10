# 🔄 HƯỚNG DẪN RE-IMPORT DATABASE

## ⚠️ Vấn đề kết nối Neo4j

Hiện tại không kết nối được Neo4j (có thể server đang sleep hoặc firewall block).

**Error:** `Unable to retrieve routing information` khi connect tới `34.124.169.171:7687`

## ✅ Giải pháp

### Option 1: Dùng Neo4j Browser (RECOMMENDED)

1. **Truy cập Neo4j Aura Console:**
   - Vào https://console.neo4j.io/
   - Login vào account của bạn
   - Kiểm tra instance có đang chạy không

2. **Nếu instance đang paused/sleeping:**
   - Click "Resume" để wake up instance
   - Đợi ~1-2 phút cho instance khởi động

3. **Mở Neo4j Browser:**
   - Click "Open" → "Neo4j Browser"
   - Hoặc connect tới: https://workspace-...-neo4j.io/browser/

4. **Xóa toàn bộ data:**
   ```cypher
   // Step 1: Xóa tất cả nodes và relationships
   MATCH (n) DETACH DELETE n;
   ```
   
   **Lưu ý:** Query này có thể chạy lâu (~30-60 giây) nếu có nhiều data

5. **Verify đã xóa:**
   ```cypher
   // Kiểm tra còn bao nhiêu nodes
   MATCH (n) RETURN count(n) as nodes;
   
   // Should return: nodes = 0
   ```

6. **Re-import từ local:**
   ```bash
   cd /home/phuc/workspace/school/vn-football-graph
   .venv/bin/python -m neo4j_import.import_to_neo4j
   ```

### Option 2: Chờ instance tự wake up

Nếu instance đang sleep, nó sẽ tự wake up khi có connection attempt.

**Thử lại sau 2-3 phút:**
```bash
.venv/bin/python reimport_database.py
```

### Option 3: Restart instance

1. Vào Neo4j Aura Console
2. Click "..." (menu) → "Restart"
3. Đợi instance restart (~2-3 phút)
4. Thử connect lại

## 📋 Chi tiết Re-import Process

### Bước 1: Xóa data cũ

**Qua Neo4j Browser:**
```cypher
MATCH (n) DETACH DELETE n;
```

**Hoặc qua script (nếu connect được):**
```bash
.venv/bin/python -c "
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

with driver.session() as session:
    session.run('MATCH (n) DETACH DELETE n')
    print('✅ Data cleared')

driver.close()
"
```

### Bước 2: Re-import data

```bash
cd /home/phuc/workspace/school/vn-football-graph
.venv/bin/python -m neo4j_import.import_to_neo4j
```

**Expected output:**
```
Loading parsed data...
  ✓ Loaded 526 players
  ✓ Loaded 78 clubs
  ✓ Loaded 272 competitions
  ✓ Loaded 67 provinces
  ✓ Loaded 63 coaches
  ✓ Loaded 41 stadiums
  ✓ Loaded 13 national teams

Importing to Neo4j...
  ✓ Created 1060 nodes
  ✓ Created 36184 relationships

✅ Import completed successfully!
```

### Bước 3: Verify

**Check node counts:**
```cypher
MATCH (n)
RETURN labels(n)[0] as label, count(*) as count
ORDER BY count DESC;
```

**Expected:**
```
Player: 526
Competition: 272
Club: 78
Province: 67
Coach: 63
Stadium: 41
NationalTeam: 13
TOTAL: 1,060 nodes
```

**Check relationship counts:**
```cypher
MATCH ()-[r]->()
RETURN type(r) as type, count(*) as count
ORDER BY count DESC
LIMIT 10;
```

**Expected:**
```
NATIONAL_TEAMMATE: 24,498
TEAMMATE: 8,104
PLAYED_FOR: 1,060
PLAYED_FOR_NATIONAL: 683
...
TOTAL: 36,184 relationships
```

## 🚨 Troubleshooting

### "Unable to retrieve routing information"

**Nguyên nhân:**
- Instance đang sleep/paused
- Firewall blocking port 7687
- Instance đang restart

**Giải pháp:**
1. Check instance status trên Aura Console
2. Resume nếu paused
3. Đợi 2-3 phút
4. Thử lại

### "Connection timeout"

**Nguyên nhân:**
- Network issue
- Instance overloaded

**Giải pháp:**
1. Check internet connection
2. Try từ browser trước (Neo4j Browser)
3. Nếu browser ok, issue là local network

### Import script báo lỗi

**Nguyên nhân:**
- Thiếu data files trong data/parsed/

**Giải pháp:**
```bash
# Check data files exist
ls data/parsed/

# Should see:
# players.jsonl
# clubs.jsonl
# coaches.jsonl
# ...
```

Nếu thiếu, cần re-parse từ raw data:
```bash
python -m parser.infobox_parser --parse-all
python -m processor.entity_builder
python -m processor.relationship_builder
```

## 💡 Quick Commands

```bash
# 1. Check if Neo4j is accessible
.venv/bin/python -c "from neo4j import GraphDatabase; from dotenv import load_dotenv; import os; load_dotenv(); driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))); print('✅ Connected'); driver.close()"

# 2. Clear database (if connected)
.venv/bin/python -c "from neo4j import GraphDatabase; from dotenv import load_dotenv; import os; load_dotenv(); driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))); driver.session().run('MATCH (n) DETACH DELETE n'); print('✅ Cleared'); driver.close()"

# 3. Re-import
.venv/bin/python -m neo4j_import.import_to_neo4j

# 4. Verify
.venv/bin/python -c "from neo4j import GraphDatabase; from dotenv import load_dotenv; import os; load_dotenv(); driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))); session = driver.session(); nodes = session.run('MATCH (n) RETURN count(n)').single()[0]; rels = session.run('MATCH ()-[r]->() RETURN count(r)').single()[0]; print(f'Nodes: {nodes}, Rels: {rels}'); driver.close()"
```

## 📝 Next Steps Sau khi Re-import

1. ✅ Restart chatbot để reload cache:
   ```bash
   # Chatbot sẽ auto-reload khi chạy lần sau
   .venv/bin/python chat.py
   ```

2. ✅ Test queries:
   ```bash
   # Test 1-hop
   "Công Phượng chơi cho đội nào?"
   
   # Test 2-hop
   "Đồng đội của Quang Hải sinh ở tỉnh nào?"
   ```

3. ✅ Check accuracy:
   ```bash
   .venv/bin/python test_multihop.py
   ```

---

**Status:** Đang chờ Neo4j instance wake up hoặc manual clear qua Browser
