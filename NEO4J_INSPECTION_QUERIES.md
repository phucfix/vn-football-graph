# 📊 NEO4J DATABASE INSPECTION QUERIES

## 1. Thống kê tổng quan

### Đếm tổng số nodes và relationships
```cypher
MATCH (n)
RETURN count(n) as total_nodes;
```

```cypher
MATCH ()-[r]->()
RETURN count(r) as total_relationships;
```

### Đếm nodes theo label
```cypher
MATCH (n)
RETURN labels(n)[0] as label, count(n) as count
ORDER BY count DESC;
```

### Đếm relationships theo type
```cypher
MATCH ()-[r]->()
RETURN type(r) as rel_type, count(r) as count
ORDER BY count DESC;
```

---

## 2. Kiểm tra dữ liệu sau khi xóa text_extraction

### Đếm relationships theo source
```cypher
MATCH ()-[r]->()
WHERE r.source IS NOT NULL
RETURN r.source as source, count(r) as count
ORDER BY count DESC;
```

### Kiểm tra xem còn text_extraction không
```cypher
MATCH ()-[r]->()
WHERE r.source = 'text_extraction'
RETURN count(r) as text_extraction_count;
```

*Kết quả mong đợi: 0 (đã xóa hết)*

---

## 3. Kiểm tra Công Phượng cụ thể

### Tìm player node
```cypher
MATCH (p:Player)
WHERE p.name CONTAINS 'Công Phượng'
RETURN p.name, p.wiki_id, p.birth_date;
```

### Xem tất cả relationships của Công Phượng
```cypher
MATCH (p:Player {name: 'Nguyễn Công Phượng'})-[r]-(other)
RETURN type(r) as rel_type, 
       labels(other)[0] as other_label,
       other.name as other_name,
       r.source as source
ORDER BY rel_type, other_name;
```

### Đếm số CLB của Công Phượng
```cypher
MATCH (p:Player {name: 'Nguyễn Công Phượng'})-[r:PLAYED_FOR]->(c:Club)
RETURN count(c) as club_count;
```

*Kết quả mong đợi: 0 (đã xóa hết text_extraction, chưa có data từ infobox)*

### Xem chi tiết CLB của Công Phượng (nếu có)
```cypher
MATCH (p:Player {name: 'Nguyễn Công Phượng'})-[r:PLAYED_FOR]->(c:Club)
RETURN c.name as club, r.source as source, r.confidence as confidence
ORDER BY c.name;
```

---

## 4. Sample data

### Lấy 10 players mẫu
```cypher
MATCH (p:Player)
RETURN p.name, p.wiki_id, p.birth_date
LIMIT 10;
```

### Lấy 10 PLAYED_FOR relationships mẫu
```cypher
MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club)
RETURN p.name as player, c.name as club, r.source as source
LIMIT 10;
```

### Xem players có nhiều CLB nhất
```cypher
MATCH (p:Player)-[r:PLAYED_FOR]->(c:Club)
WITH p, count(c) as club_count
WHERE club_count > 5
RETURN p.name, club_count
ORDER BY club_count DESC
LIMIT 10;
```

---

## 5. Kiểm tra quality

### Tìm players không có relationships nào
```cypher
MATCH (p:Player)
WHERE NOT (p)-[]-()
RETURN p.name, p.wiki_id
LIMIT 10;
```

### Tìm relationships có confidence thấp
```cypher
MATCH ()-[r]->()
WHERE r.confidence IS NOT NULL AND r.confidence < 0.5
RETURN type(r) as rel_type, r.confidence, r.source, r.context
LIMIT 20;
```

---

## 6. Graph visualization

### Visualize Công Phượng và các connections
```cypher
MATCH path = (p:Player {name: 'Nguyễn Công Phượng'})-[*1..2]-(other)
RETURN path
LIMIT 50;
```

### Visualize sample graph
```cypher
MATCH path = (p:Player)-[:PLAYED_FOR]->(c:Club)<-[:PLAYED_FOR]-(p2:Player)
WHERE p.name = 'Nguyễn Quang Hải'
RETURN path
LIMIT 25;
```

---

## 📝 Ghi chú

**Sau khi chạy các queries này, bạn sẽ biết:**

1. ✅ Tổng số nodes và relationships hiện tại
2. ✅ Dữ liệu text_extraction đã được xóa sạch chưa (should be 0)
3. ✅ Công Phượng hiện có bao nhiêu CLB (should be 0 after cleanup)
4. ✅ Cần re-import data từ đâu (infobox parser hoặc CSV)

**Trạng thái mong đợi sau cleanup:**
- `text_extraction` relationships: **0** ✅
- Công Phượng PLAYED_FOR: **0** (cần re-import)
- Total relationships: Giảm ~2,481 so với trước
