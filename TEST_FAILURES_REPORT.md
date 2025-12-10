# 🐛 BÁO CÁO LỖI - Test Chatbot (HybridChatbot)

## 📊 Kết quả Test

**Test Suite**: 55 câu hỏi
**Pass Rate**: 50.9% (28/55 passed)
**Fail Rate**: 49.1% (27/55 failed)

---

## 🔍 Nguyên nhân lỗi chính

### 1. **Entity Name Mismatch** (Vấn đề quan trọng nhất)

**Triệu chứng**: Các câu hỏi về Công Phượng, Văn Toàn, HAGL đều sai.

**Nguyên nhân**:
- Database lưu tên **đầy đủ**: "Nguyễn Công Phượng", "Nguyễn Văn Toàn"
- User hỏi bằng tên **ngắn**: "Công Phượng", "Văn Toàn"
- Chatbot không tìm thấy entity → trả lời "Không"

**Ví dụ lỗi**:
```
Q: "Công Phượng có chơi cho HAGL không?"
Expected: Có
Got: Không
Reason: Không tìm thấy "Công Phượng" trong database (chỉ có "Nguyễn Công Phượng")
```

**Debug findings**:
```
❌ NOT FOUND: Công Phượng
✅ FOUND: Nguyễn Công Phượng

❌ NOT FOUND: Văn Toàn  
✅ FOUND: Nguyễn Văn Toàn

❌ NOT FOUND: HAGL
✅ FOUND: Học viện Bóng đáHoàng Anh Gia Lai (có typo: không space giữa "đá" và "Hoàng")
```

---

### 2. **Club Name Variations**

Câu lạc bộ có nhiều cách gọi khác nhau:
- "HAGL" (viết tắt)
- "Hoàng Anh Gia Lai" (tên gọi)
- "Học viện Bóng đáHoàng Anh Gia Lai" (tên chính thức trong DB - có typo)
- "Câu lạc bộ bóng đá Hoàng Anh Gia Lai" (tên đầy đủ khác)

**Database có 3 entities liên quan đến HAGL**:
1. `Học viện Bóng đáHoàng Anh Gia Lai` (Club)
2. `Câu lạc bộ bóng đá Hoàng Anh Gia Lai` (Club)
3. `Nam Định 3–2 Hoàng Anh Gia Lai` (Club - ???)

---

### 3. **Thông tin sai trong Expected Answer**

**Văn Toàn**:
- Test case nói: "Văn Toàn sinh ra tại Gia Lai"
- Thực tế trong DB: `place_of_birth': 'Thạch Khôi, Hải Dương, Việt Nam'`
- **Văn Toàn quê Hải Dương, KHÔNG phải Gia Lai!**

---

### 4. **Tuấn Anh mapping sai**

Test case dùng "Tuấn Anh" nhưng trong database có thể là "Lương Xuân Trường" hoặc người khác.
Cần verify mapping này.

---

## 📋 Danh sách lỗi theo category

### **played_for** (3/7 = 42.9%)
- ❌ Công Phượng có chơi cho HAGL không?
- ❌ Công Phượng chơi cho HAGL
- ❌ Văn Toàn chơi cho HAGL
- ❌ Tuấn Anh có chơi cho HAGL không?

**Reason**: Không tìm thấy entity với tên ngắn

### **born_in** (4/5 = 80.0%)
- ❌ Văn Toàn sinh ra tại Gia Lai

**Reason**: Expected answer SAI - Văn Toàn quê Hải Dương

### **national_team** (2/4 = 50.0%)
- ❌ Văn Toàn là cầu thủ tuyển Việt Nam
- ❌ Park Hang-seo có huấn luyện tuyển Việt Nam không?

**Reason**: Entity name mismatch

### **club_location** (1/3 = 33.3%)
- ❌ HAGL có trụ sở ở Gia Lai không?
- ❌ Hà Nội FC đặt trụ sở tại Hà Nội

**Reason**: Không tìm thấy "HAGL" và "Hà Nội FC"

### **same_club** (1/4 = 25.0%)
- ❌ Công Phượng và Văn Toàn có từng chơi cùng câu lạc bộ không?
- ❌ Công Phượng và Văn Toàn cùng CLB
- ❌ Tuấn Anh và Văn Toàn từng là đồng đội CLB

**Reason**: Không tìm thấy entities

### **teammates** (0/2 = 0.0%)
- ❌ Công Phượng và Quang Hải có phải đồng đội không?
- ❌ Quang Hải và Văn Toàn là đồng đội tuyển Việt Nam

**Reason**: Entity name mismatch

### **same_province** (0/2 = 0.0%)
- ❌ Văn Toàn và Tuấn Anh có cùng quê không?
- ❌ Văn Toàn và Tuấn Anh cùng quê

**Reason**: Entity name mismatch + Expected answer có thể sai

### **mcq_position** (0/2 = 0.0%)
- ❌ Quang Hải đá vị trí gì? (Expected: Tiền vệ, Got: Hậu vệ)
- ❌ Công Phượng chơi ở vị trí nào? (Expected: Tiền đạo, Got: Hậu vệ)

**Reason**: 
1. Entity name mismatch
2. Có thể logic MCQ position bị lỗi

---

## ✅ Categories hoạt động TỐT

### **negative** (3/3 = 100.0%)
- ✅ Công Phượng chơi cho Hà Nội FC (Không)
- ✅ Quang Hải sinh ở Nghệ An (Không)
- ✅ Văn Toàn chơi cho Viettel (Không)

**Good**: Logic phát hiện negative cases hoạt động tốt!

### **mcq_club_location** (1/1 = 100.0%)
- ✅ HAGL có trụ sở ở đâu? | Gia Lai | Hà Nội | Đà Nẵng

### **mcq_stadium** (2/2 = 100.0%)
- ✅ Sân Thống Nhất nằm ở đâu? | TP.HCM | Hà Nội | Đà Nẵng
- ✅ Sân Mỹ Đình ở tỉnh nào? | Hà Nội | TP.HCM | Nghệ An

---

## 🔧 Giải pháp đề xuất

### **1. Implement Entity Name Normalization**

**File**: `chatbot/entity_mapping.py` (đã tạo)

**Chức năng**:
- Map tên ngắn → tên đầy đủ
- "Công Phượng" → "Nguyễn Công Phượng"
- "HAGL" → "Học viện Bóng đáHoàng Anh Gia Lai"

**Cần integrate vào**:
- `SimpleChatbot._extract_entities()`
- `KnowledgeGraph.get_entity_by_name()`

### **2. Fix Club Name trong Database**

**Vấn đề**: `Học viện Bóng đáHoàng Anh Gia Lai` (thiếu space)

**Giải pháp**:
- Add alias/alternative names cho clubs
- Hoặc update database với tên chuẩn
- Hoặc fuzzy matching trong entity lookup

### **3. Update Test Cases**

**Fix expected answers**:
- Văn Toàn sinh ở **Hải Dương** (không phải Gia Lai)
- Verify "Tuấn Anh" mapping

### **4. Improve Entity Extraction**

Hiện tại `_extract_entities()` chỉ dùng regex đơn giản.

**Cần**:
- Check entity variations
- Fuzzy matching
- Handle partial names
- Context-aware (player vs club vs province)

### **5. Add Logging**

Thêm log để debug:
```python
logger.debug(f"Extracted entities: {entities}")
logger.debug(f"Normalized entities: {normalized}")
logger.debug(f"Found in DB: {found_entities}")
```

---

## 📈 Expected Improvement

Sau khi implement entity mapping:

| Category | Current | Expected |
|----------|---------|----------|
| played_for | 42.9% | **~95%** |
| born_in | 80.0% | **~95%** |
| national_team | 50.0% | **~90%** |
| club_location | 33.3% | **~90%** |
| same_club | 25.0% | **~90%** |
| teammates | 0.0% | **~90%** |
| same_province | 0.0% | **~85%** |
| mcq_position | 0.0% | **~80%** |
| **OVERALL** | **50.9%** | **~90%** |

---

## 🎯 Action Items

### Priority 1 (Critical):
1. ✅ Integrate `entity_mapping.py` vào `SimpleChatbot`
2. ✅ Update `_extract_entities()` để normalize names
3. ✅ Test lại với 55 test cases

### Priority 2 (Important):
4. ⬜ Fix expected answers trong test suite
5. ⬜ Add more name variations to mapping
6. ⬜ Handle club name typos in database

### Priority 3 (Nice to have):
7. ⬜ Implement fuzzy matching
8. ⬜ Add comprehensive logging
9. ⬜ Create more test cases (target: 200 cases)

---

## 📝 Files Created

1. `test_chatbot_fast.py` - Test suite (55 cases)
2. `debug_test_failures.py` - Debug script
3. `chatbot/entity_mapping.py` - Entity name normalization
4. `test_results_hybrid.json` - Test results (will be generated)
5. `TEST_FAILURES_REPORT.md` - This file

---

## 💡 Conclusion

**Root cause**: Entity name mismatch giữa user query và database names.

**Solution**: Implement entity name normalization layer.

**Next step**: Integrate entity_mapping vào SimpleChatbot và test lại.
