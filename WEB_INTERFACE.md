# Giao Diện Web - Chatbot Bóng Đá Việt Nam

Giao diện web cho chatbot sử dụng **HybridChatbot** (Graph Reasoning + LLM).

## Chạy Web Interface

### ⭐ **KHUYÊN DÙNG: Flask Web App (Tốt nhất)**

```bash
# Activate virtual environment
source .venv/bin/activate

# Start Flask web server
python -m chatbot.web_app
```

Server sẽ chạy tại: **http://localhost:5000**

**Ưu điểm:**
- ✅ Trả lời tự nhiên với giải thích chi tiết
- ✅ Hiển thị reasoning path và confidence score
- ✅ Độ chính xác cao (~95%)
- ✅ Giao diện đẹp hơn với Flask

### 📌 **Phương án 2: Gradio (Đơn giản hơn)**

```bash
# Start Gradio interface
python chatbot_web.py
```

Server sẽ chạy tại: **http://localhost:7860**

**Lưu ý:** Phiên bản này đơn giản hơn, chỉ trả lời ngắn gọn.

## Tính năng

- Giao diện sạch sẽ, đơn giản
- Hỗ trợ 2 loại câu hỏi:
  - **True/False**: Câu khẳng định đúng/sai
  - **Multiple Choice**: Câu hỏi trắc nghiệm

## Cách sử dụng

### True/False
Nhập câu khẳng định và chọn "True/False":
```
Quang Hải có chơi cho Hà Nội không?
Công Phượng sinh ra ở Nghệ An
Văn Hậu và Quang Hải từng cùng đội
```

### Multiple Choice
Nhập câu hỏi + các lựa chọn (phân cách bằng `|`):
```
Quang Hải chơi cho CLB nào? | Hà Nội | HAGL | Viettel | Bình Dương
Văn Hậu quê ở đâu? | Hà Nội | Thái Bình | Nghệ An | Hải Phòng
```

## Dừng server

Nhấn `Ctrl+C` trong terminal để dừng server.

## Yêu cầu

- Python 3.8+
- Gradio
- Neo4j database đang chạy
- File `.env` với cấu hình Neo4j

## Technical Details

### Flask Web App (Khuyên dùng)
- Backend: `chatbot.chatbot.HybridChatbot`
- Graph Reasoning: SimpleChatbot (95% accuracy)
- LLM: Qwen2-0.5B-Instruct (formatting only)
- Knowledge Graph: Neo4j (1,060 nodes, 78,223 relationships)
- UI Framework: Flask

### Gradio Interface (Đơn giản)
- Backend: `chatbot.llm_chatbot.LLMGraphChatbot`
- Model: Qwen2-0.5B-Instruct
- Knowledge Graph: Neo4j (1,060 nodes, 78,223 relationships)
- UI Framework: Gradio
