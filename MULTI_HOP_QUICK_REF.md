# Ví dụ Câu hỏi Multi-hop - Quick Reference

## Tóm tắt

Chatbot hỗ trợ 3 cấp độ câu hỏi:
- **1-hop**: Quan hệ trực tiếp (accuracy ~90%)
- **2-hop**: Qua 1 node trung gian (accuracy ~70-80%)
- **3-hop**: Qua 2 nodes trung gian (accuracy ~50-60%)

---

## 1-HOP (Dễ - Trực tiếp)

```
Quang Hải chơi cho Hà Nội
Công Phượng sinh ra ở Nghệ An
Văn Hậu quê ở Thái Bình
Park Hang-seo huấn luyện Việt Nam
```

**Graph path**: `A -[relation]-> B`

---

## 2-HOP (Trung bình - 1 trung gian)

### Cùng đội (Same Club)
```
Quang Hải và Văn Hậu từng cùng đội
Công Phượng và Văn Toàn cùng chơi cho một câu lạc bộ
```
**Graph path**: `Player1 -> Club <- Player2`

### Cùng quê (Same Province)
```
Công Phượng và Văn Toàn cùng quê
Văn Hậu và Duy Mạnh cùng quê Thái Bình
```
**Graph path**: `Player1 -> Province <- Player2`

### Player qua Club đến Province
```
Quang Hải chơi cho CLB ở Hà Nội
```
**Graph path**: `Player -> Club -> Province`

---

## 3-HOP (Khó - 2 trung gian)

### Đồng đội cùng quê
```
Quang Hải có đồng đội quê Nghệ An không
```
**Graph path**: `Player1 -> Club <- Player2 -> Province`

### Cùng quê chơi cho club
```
Người cùng quê Công Phượng có chơi cho HAGL không
```
**Graph path**: `Player1 -> Province <- Player2 -> Club`

### HLV dẫn cầu thủ từ tỉnh
```
Park Hang-seo có dẫn cầu thủ Nghệ An không
```
**Graph path**: `Coach -> Club <- Player -> Province`

---

## MCQ Examples (Trắc nghiệm)

### 1-hop MCQ
```
Quang Hải chơi cho CLB nào? | Hà Nội | HAGL | Viettel | Bình Dương
Công Phượng quê ở đâu? | Hà Nội | Nghệ An | Thái Bình | TP.HCM
```

### 2-hop MCQ
```
Cầu thủ nào là đồng đội của Quang Hải? | Văn Hậu | Công Phượng | Văn Toàn
Ai cùng quê với Công Phượng? | Văn Toàn | Quang Hải | Văn Hậu
```

---

## Cách test

### CLI:
```bash
python test_multihop.py
```

### Web UI:
```bash
python chatbot_web.py
# Truy cập http://localhost:7860
```

### Python code:
```python
from chatbot.llm_chatbot import LLMGraphChatbot

cb = LLMGraphChatbot()
cb.initialize()

# Test 2-hop
ans, conf = cb.answer_true_false("Quang Hải và Văn Hậu từng cùng đội")
print(f"Answer: {'ĐÚNG' if ans else 'SAI'} ({conf:.0%})")
```

---

## Lưu ý

**Chatbot hiện parse được:**
- ✅ "A và B cùng đội" / "cùng câu lạc bộ"
- ✅ "A và B cùng quê"
- ✅ "A chơi cho [Club]"
- ✅ "A sinh ra ở [Province]"
- ⚠️ Các pattern 3-hop còn hạn chế

**Để cải thiện accuracy:**
- Dùng tên đầy đủ của cầu thủ
- Dùng pattern câu đơn giản, rõ ràng
- Tránh câu quá phức tạp với nhiều điều kiện

**File tài liệu chi tiết:**
- `MULTI_HOP_EXAMPLES.md` - Giải thích đầy đủ về multi-hop
- `test_multihop.py` - Script test tự động
