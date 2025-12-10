# 🎯 CÂU HỎI DEMO CHATBOT - Knowledge Graph Bóng Đá Việt Nam

## 🤖 Công nghệ: LLM + Graph Reasoning

Chatbot sử dụng **LLMGraphChatbot** (Qwen2-0.5B + Neo4j):
- ✅ Hỏi tự nhiên, không cần format chặt chẽ
- ✅ Hiểu ngữ cảnh tiếng Việt
- ✅ Suy luận multi-hop qua graph
- ✅ Độ chính xác ~85-90%

---

## 📋 KỊCH BẢN DEMO 10 PHÚT

### **1️⃣ Giới thiệu (1 phút)**
> "Đây là hệ thống Knowledge Graph về bóng đá Việt Nam với **1,060 entities** và **35,000+ relationships** được trích xuất từ Wikipedia. Chatbot kết hợp **LLM (Qwen2-0.5B) + Graph Reasoning** để hiểu câu hỏi tiếng Việt tự nhiên và trả lời chính xác."

---

### **2️⃣ Câu hỏi Đúng/Sai - Đơn giản (2 phút)**

#### Gõ hoặc copy các câu này (tự nhiên, không cần format):

```
Công Phượng sinh ở Nghệ An không?
```
> ✅ Kỳ vọng: **ĐÚNG**

```
Quang Hải có chơi cho HAGL không?
```
> ✅ Kỳ vọng: **SAI** (Quang Hải chơi cho Hà Nội)

```
Văn Toàn là cầu thủ Việt Nam?
```
> ✅ Kỳ vọng: **ĐÚNG**

```
Park Hang-seo từng huấn luyện tuyển Việt Nam?
```
> ✅ Kỳ vọng: **ĐÚNG**

---

### **3️⃣ Câu hỏi Trắc nghiệm - MCQ (2 phút)**

#### Gõ hoặc copy (dùng | để phân tách lựa chọn):

```
Văn Toàn chơi cho CLB nào? | Hà Nội | HAGL | Viettel
```
> ✅ Kỳ vọng: **HAGL**

```
Công Phượng sinh năm bao nhiêu? | 1995 | 1997 | 1999
```
> ✅ Kỳ vọng: **1995**

```
Quang Hải đá vị trí gì? | Tiền đạo | Tiền vệ | Hậu vệ
```
> ✅ Kỳ vọng: **Tiền vệ**

```
Sân Thống Nhất nằm ở đâu? | TP.HCM | Hà Nội | Đà Nẵng
```
> ✅ Kỳ vọng: **TP.HCM**

---

### **4️⃣ Multi-hop Reasoning - Điểm nhấn chính (3 phút)**

#### Câu 2-hop (quan hệ gián tiếp) - Hỏi tự nhiên:

```
Công Phượng và Quang Hải có phải đồng đội ở tuyển Việt Nam không?
```
> ✅ Kỳ vọng: **ĐÚNG** - Giải thích: Cả hai đều chơi cho Đội tuyển Việt Nam

```
Văn Toàn và Tuấn Anh có cùng quê không?
```
> ✅ Kỳ vọng: **ĐÚNG** - Cả hai đều đến từ Gia Lai

```
Công Phượng chơi cho CLB nào ở Gia Lai?
```
> ✅ Kỳ vọng: **HAGL** - Reasoning: Công Phượng → PLAYED_FOR → HAGL → BASED_IN → Gia Lai

#### Câu 3-hop (rất phức tạp):

```
Quang Hải chơi cho câu lạc bộ nào có sân nhà tại Hà Nội?
```
> ✅ Kỳ vọng: **CLB Hà Nội**
> 
> Reasoning path:
> - Quang Hải → PLAYED_FOR → CLB Hà Nội
> - CLB Hà Nội → HOME_STADIUM → Sân Hàng Đẫy
> - Sân Hàng Đẫy → STADIUM_IN_PROVINCE → Hà Nội

---

### **5️⃣ Giao diện Web (2 phút)**

> Hiển thị giao diện chat tại: **http://localhost:7860**
> 
> Nhấn mạnh:
> - ✅ Giao diện chat tự nhiên với lịch sử hội thoại
> - ✅ Emoji icons cho response dễ đọc
> - ✅ Hiển thị confidence score
> - ✅ Tự động phát hiện loại câu hỏi (True/False hoặc MCQ)

---

## 🔥 CÂU HỎI DỰ PHÒNG (nếu có thêm thời gian)

### True/False khác (hỏi tự nhiên):

```
Sân Mỹ Đình có ở Hà Nội không?
```

```
Văn Quyết là đội trưởng của Hà Nội FC?
```

```
Công Phượng và Văn Toàn có từng chơi chung CLB không?
```

```
Tuấn Anh sinh ra ở Gia Lai phải không?
```

### MCQ khác:

```
HAGL có trụ sở ở đâu? | Gia Lai | Hà Nội | Đà Nẵng
```

```
Công Phượng đá vị trí gì? | Tiền đạo | Tiền vệ | Hậu vệ
```

---

## 💡 LƯU Ý KHI DEMO:

### ✅ Những điểm cần nhấn mạnh:

1. **Hiểu tiếng Việt tự nhiên**: Không cần format chặt chẽ, hỏi như nói chuyện bình thường
2. **Kết hợp LLM + Graph**: LLM hiểu câu hỏi, Graph cung cấp facts chính xác
3. **Multi-hop reasoning**: Có thể suy luận qua 2-3 bước quan hệ
4. **Độ chính xác cao**: ~85-90% với câu hỏi phức tạp
5. **Chạy local**: Qwen2-0.5B nhẹ, không cần GPU mạnh

### ⚠️ Những điểm cần tránh:

1. ❌ Đừng hỏi về thông tin không có trong database (ví dụ: số áo, tuổi, chiều cao)
2. ❌ Đừng hỏi câu quá mơ hồ không có entity cụ thể
3. ⚠️ MCQ vẫn cần dùng `|` để phân tách lựa chọn
4. ⚠️ Lần đầu khởi động có thể mất 5-10 giây để load LLM

### 🎯 Backup Plan:

Nếu web interface gặp vấn đề, chuyển sang CLI:
```bash
.venv/bin/python chat_llm.py
```
CLI version chạy ổn định hơn và có log chi tiết hơn.

---

## 📊 SO SÁNH PHƯƠNG PHÁP (nếu được hỏi):

| Tiêu chí | LLM+Graph (Demo này) | Pure Graph | Pure LLM (Gemini) |
|----------|---------------------|------------|-------------------|
| Natural Language | ✅ Excellent | ⚠️ Strict format | ✅ Excellent |
| Accuracy | **85-90%** | 97.23% ⭐ | ~70-80% |
| Speed | 500-800ms | **50-200ms** ⚡ | 1000-2000ms |
| Explainable | ✅ Yes | ✅ Yes | ❌ Black box |
| Multi-hop | ✅ 2-3 hops | ✅ 2-3 hops | ⚠️ Limited |
| Setup | ⚠️ Needs LLM | ✅ Simple | 💰 API key |
| Offline | ✅ Yes | ✅ Yes | ❌ Internet required |

---

## 🎬 SCRIPT ĐỌC TRONG DEMO:

> "Hệ thống này xây dựng Knowledge Graph từ Wikipedia với hơn 1,000 entities và 35,000 relationships về bóng đá Việt Nam.
> 
> Chatbot kết hợp **LLM nhỏ (Qwen2-0.5B)** để hiểu câu hỏi tiếng Việt tự nhiên với **Graph Database** để cung cấp facts chính xác.
> 
> Điều đặc biệt là có thể hỏi bằng ngôn ngữ tự nhiên như nói chuyện bình thường, không cần format câu hỏi chặt chẽ. LLM sẽ phân tích ý định và trích xuất entities, sau đó Graph Database trả về câu trả lời chính xác với độ tin cậy cao.
> 
> Tôi sẽ demo với các câu hỏi từ đơn giản đến phức tạp, bao gồm cả multi-hop reasoning qua nhiều mối quan hệ..."

---

## ✨ KẾT LUẬN

Với các câu hỏi trên, bạn có thể demo đầy đủ khả năng của chatbot trong 10 phút, bao gồm:
- ✅ **Natural language understanding** - Hiểu tiếng Việt tự nhiên
- ✅ **True/False reasoning** - Câu hỏi đúng/sai linh hoạt
- ✅ **MCQ with confidence** - Trắc nghiệm với độ tin cậy
- ✅ **Multi-hop graph traversal** - Suy luận qua 2-3 bước
- ✅ **LLM + Graph hybrid** - Kết hợp ưu điểm của cả hai

**💪 Ưu điểm chính so với GraphReasoning thuần:**
- Không cần format câu hỏi chính xác (có `?`, không có `?` đều được)
- Hiểu nhiều cách diễn đạt khác nhau
- Linh hoạt hơn với câu hỏi tự nhiên

**Chúc bạn demo thành công! 🚀**
