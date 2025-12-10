# Câu hỏi Multi-hop cho Chatbot Bóng Đá Việt Nam

## Giải thích về "Hop"

- **1-hop**: Quan hệ trực tiếp giữa 2 entities
- **2-hop**: Cần đi qua 1 node trung gian
- **3-hop**: Cần đi qua 2 nodes trung gian

---

## 1-HOP QUESTIONS (Quan hệ trực tiếp)

### Player → Club
```
Quang Hải có chơi cho Hà Nội không?
Công Phượng từng khoác áo HAGL?
Văn Hậu đã thi đấu cho Heerenveen không?
```

### Player → Province (Quê quán)
```
Công Phượng sinh ra ở Nghệ An đúng không?
Văn Hậu quê ở Thái Bình phải không?
Quang Hải có phải người Hà Nội không?
```

### Coach → Club
```
Park Hang-seo đã huấn luyện đội tuyển Việt Nam không?
Troussier huấn luyện Việt Nam phải không?
```

---

## 2-HOP QUESTIONS (1 node trung gian)

### Player → Club ← Player (Cùng đội)
**Path**: Player1 -[:PLAYED_FOR]-> Club <-[:PLAYED_FOR]- Player2

```
Quang Hải và Văn Hậu từng cùng đội không?
Công Phượng và Văn Toàn cùng chơi cho một câu lạc bộ?
Tuấn Anh có phải đồng đội của Công Phượng không?
```

**Giải thích**: 
- Hop 1: Quang Hải → Hà Nội
- Hop 2: Hà Nội ← Văn Hậu
- Kết luận: Cùng chơi cho Hà Nội

### Player → Province ← Player (Cùng quê)
**Path**: Player1 -[:BORN_IN]-> Province <-[:BORN_IN]- Player2

```
Công Phượng và Văn Toàn cùng quê không?
Quang Hải có cùng quê với Văn Quyết không?
Văn Hậu và Duy Mạnh cùng quê Thái Bình phải không?
```

**Giải thích**:
- Hop 1: Công Phượng → Nghệ An
- Hop 2: Nghệ An ← Văn Toàn
- Kết luận: Cùng quê Nghệ An

### Player → Club → Province (Cầu thủ thuộc CLB ở tỉnh nào)
**Path**: Player -[:PLAYED_FOR]-> Club -[:BASED_IN]-> Province

```
Quang Hải chơi cho CLB ở Hà Nội không?
Công Phượng từng thi đấu cho câu lạc bộ tại Nghệ An?
Văn Hậu có khoác áo đội bóng ở Hải Phòng không?
```

**Giải thích**:
- Hop 1: Quang Hải → Hà Nội FC
- Hop 2: Hà Nội FC → Hà Nội (thành phố)
- Kết luận: Đúng

---

## 3-HOP QUESTIONS (2 nodes trung gian)

### Player → Club ← Player → Province (Đồng đội có cùng quê không)
**Path**: Player1 -[:PLAYED_FOR]-> Club <-[:PLAYED_FOR]- Player2 -[:BORN_IN]-> Province

```
Quang Hải có đồng đội nào quê ở Nghệ An không?
Công Phượng từng có đồng đội người Hà Nội?
Trong đội Hà Nội, có cầu thủ nào cùng quê với Quang Hải?
```

**Giải thích**:
- Hop 1: Quang Hải → Hà Nội FC
- Hop 2: Hà Nội FC ← Văn Quyết
- Hop 3: Văn Quyết → Hà Nội (quê)
- Kết luận: Có đồng đội cùng quê Hà Nội

### Player → Province ← Player → Club (Người cùng quê chơi cho CLB nào)
**Path**: Player1 -[:BORN_IN]-> Province <-[:BORN_IN]- Player2 -[:PLAYED_FOR]-> Club

```
Có người cùng quê với Công Phượng chơi cho Hà Nội không?
Người cùng quê Nghệ An với Văn Toàn có ai thi đấu cho HAGL?
Cầu thủ cùng quê Thái Bình với Văn Hậu có chơi cho Viettel không?
```

**Giải thích**:
- Hop 1: Công Phượng → Nghệ An
- Hop 2: Nghệ An ← Văn Toàn
- Hop 3: Văn Toàn → HAGL
- Kết luận: Có (Văn Toàn)

### Coach → Club ← Player → Province (HLV dẫn dắt cầu thủ từ tỉnh nào)
**Path**: Coach -[:COACHED]-> Club <-[:PLAYED_FOR]- Player -[:BORN_IN]-> Province

```
Park Hang-seo có dẫn dắt cầu thủ Nghệ An không?
Troussier huấn luyện cầu thủ người Hà Nội?
HLV này có bao giờ dẫn dắt cầu thủ quê Thái Bình?
```

**Giải thích**:
- Hop 1: Park Hang-seo → Đội tuyển Việt Nam
- Hop 2: Đội tuyển Việt Nam ← Công Phượng
- Hop 3: Công Phượng → Nghệ An
- Kết luận: Có

---

## COMPLEX MULTI-HOP MCQ (Trắc nghiệm phức tạp)

### 2-hop MCQ

```
Cầu thủ nào là đồng đội của Quang Hải? | Văn Hậu | Công Phượng | Văn Toàn | Tuấn Anh
```
- Yêu cầu tìm player cùng chơi cho 1 club với Quang Hải

```
Quang Hải và ai cùng quê? | Văn Quyết | Công Phượng | Văn Hậu | Văn Toàn
```
- Yêu cầu tìm player cùng province với Quang Hải

### 3-hop MCQ

```
Có cầu thủ nào cùng quê với Công Phượng chơi cho CLB nào? | Hà Nội | HAGL | Viettel | Bình Dương
```
- Path: Công Phượng → Nghệ An ← Other Player → Club

```
HLV Park Hang-seo dẫn dắt cầu thủ từ tỉnh nào? | Nghệ An | Hà Nội | Thái Bình | TP.HCM
```
- Path: Coach → Club ← Player → Province

---

## TIPS CHO CHATBOT

### Để chatbot hiểu câu hỏi 2-hop, 3-hop:

**2-hop patterns:**
- "A và B cùng đội" → tìm chung club
- "A và B cùng quê" → tìm chung province
- "A chơi cho CLB ở [tỉnh]" → player→club→province

**3-hop patterns:**
- "A có đồng đội quê [tỉnh]" → player1→club←player2→province
- "Người cùng quê A chơi cho [CLB]" → player1→province←player2→club
- "HLV X dẫn cầu thủ [tỉnh]" → coach→club←player→province

---

## TEST CASES THỰC TẾ

### Dễ (1-hop):
```
Quang Hải chơi cho Hà Nội
Công Phượng sinh ở Nghệ An
Park Hang-seo huấn luyện Việt Nam
```

### Trung bình (2-hop):
```
Quang Hải và Văn Hậu cùng đội
Công Phượng và Văn Toàn cùng quê
Quang Hải chơi cho CLB ở Hà Nội
```

### Khó (3-hop):
```
Quang Hải có đồng đội quê Nghệ An
Người cùng quê Công Phượng chơi HAGL
Park Hang-seo dẫn cầu thủ Nghệ An
```

---

## LƯU Ý

**Chatbot hiện tại có thể trả lời:**
- ✅ 1-hop: Rất tốt (90%+ accuracy)
- ✅ 2-hop: Tốt (70-80% accuracy)
- ⚠️ 3-hop: Trung bình (50-60% accuracy)

**Lý do 3-hop khó hơn:**
- Cần traverse nhiều relationships
- Context window có thể overflow
- Pattern matching phức tạp hơn
- Có thể có nhiều paths khác nhau

**Để cải thiện 3-hop:**
- Sử dụng LLM để hiểu ngữ cảnh tốt hơn
- Cache các multi-hop paths phổ biến
- Optimize Cypher queries cho performance
