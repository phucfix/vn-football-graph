# Báo Cáo Đánh Giá Chatbot Multi-hop Reasoning
## Vietnam Football Knowledge Graph

**Ngày:** 2025-12-04 23:14:01

---

## 1. Tổng Quan

- **Tổng số câu hỏi:** 2,948
- **Độ chính xác KG Chatbot:** 78.60%
- **Độ chính xác External Chatbot:** 53.56%
- **Kết luận:** KG Chatbot outperforms external chatbot by 25.0%

---

## 2. Phân Tích Chi Tiết

### 2.1. Độ Chính Xác Theo Độ Khó (Số Hop)

| Độ Khó | Số Hop | KG Chatbot | External Chatbot |
|--------|--------|------------|------------------|
| Easy | 1 | 86.7% | 66.1% |
| Medium | 2 | 67.4% | 51.7% |
| Hard | 3 | 100.0% | 32.5% |

### 2.2. Độ Chính Xác Theo Loại Câu Hỏi

| Loại Câu Hỏi | KG Chatbot | External Chatbot |
|--------------|------------|------------------|
| Đúng/Sai | 92.4% | 57.3% |
| Có/Không | 84.8% | 48.6% |
| Trắc nghiệm | 26.0% | 61.1% |

### 2.3. Độ Chính Xác Theo Số Bước Suy Luận (Hops)

| Số Hops | KG Chatbot | External Chatbot |
|---------|------------|------------------|
| 1-hop | 86.7% | 66.1% |
| 2-hop | 67.4% | 51.7% |
| 3-hop | 100.0% | 32.5% |

---

## 3. Phân Tích So Sánh

### 3.1. Ưu Điểm của KG Chatbot

1. **Chính xác về dữ liệu cụ thể:** KG Chatbot truy vấn trực tiếp từ đồ thị tri thức, đảm bảo thông tin chính xác
2. **Khả năng suy luận multi-hop:** Có thể trả lời các câu hỏi yêu cầu nhiều bước suy luận
3. **Giải thích rõ ràng:** Có thể cung cấp đường đi reasoning trong đồ thị
4. **Không bị hallucination:** Chỉ trả lời dựa trên dữ liệu có sẵn

### 3.2. Hạn Chế

1. **Phụ thuộc vào dữ liệu:** Chỉ trả lời được nếu thông tin có trong đồ thị
2. **Cần pattern matching tốt:** Phụ thuộc vào khả năng hiểu câu hỏi
3. **Không linh hoạt:** Khó xử lý các câu hỏi ngoài phạm vi

### 3.3. So Sánh Với External Chatbot (nếu có)

| Trường hợp | Số lượng | Tỷ lệ |
|------------|----------|-------|
| Cả hai đúng | 1223 | 41.5% |
| Chỉ KG đúng | 1094 | 37.1% |
| Chỉ External đúng | 356 | 12.1% |
| Cả hai sai | 275 | 9.3% |

---

## 4. Kết Luận

⚠️ **KG Chatbot đạt hiệu suất khá** với độ chính xác 60-80%.
📈 KG Chatbot **vượt trội hơn** external chatbot 25.0% điểm.

### Đề Xuất Cải Thiện

1. Cải thiện pattern matching cho câu hỏi tiếng Việt
2. Bổ sung thêm dữ liệu vào đồ thị tri thức
3. Tối ưu hóa các query Cypher
4. Thêm các loại câu hỏi phức tạp hơn

---

*Báo cáo được tạo tự động bởi Chatbot Evaluator*
