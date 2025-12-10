#!/usr/bin/env python3
"""
Chat Interface for Vietnamese Football Chatbot
Uses LLMGraphChatbot (Qwen2-0.5B + Graph Reasoning)
"""

import logging
import gradio as gr
from chatbot.llm_chatbot import LLMGraphChatbot

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize chatbot once at startup
print("Đang khởi tạo chatbot...")
chatbot = LLMGraphChatbot()
chatbot.initialize()
print("Chatbot sẵn sàng!")


def chat_response(message: str, history: list) -> str:
    """
    Process user message and return chatbot response.
    
    Args:
        message: User message
        history: Chat history (list of [user_msg, bot_msg] pairs)
    
    Returns:
        Bot response string
    """
    if not message.strip():
        return "Vui lòng nhập câu hỏi của bạn."
    
    try:
        # Detect question type
        if "|" in message:
            # Multiple choice question
            parts = [p.strip() for p in message.split("|")]
            question = parts[0]
            choices = parts[1:]
            
            if len(choices) < 2:
                return "Câu hỏi trắc nghiệm cần ít nhất 2 lựa chọn.\n\nVí dụ: Quang Hải chơi cho CLB nào? | Hà Nội | HAGL | Viettel"
            
            # Use answer_mcq for MCQ
            answer, confidence = chatbot.answer_mcq(question, choices)
            
            # Simple response without icons or confidence
            return answer
        
        else:
            # True/False or open-ended question
            # Use answer_true_false for True/False
            answer, confidence = chatbot.answer_true_false(message)
            
            # Simple response without icons or confidence
            if confidence >= 0.5:
                if answer:
                    return "Đúng"
                else:
                    return "Sai"
            else:
                return "Không chắc chắn. Hãy thử câu hỏi khác hoặc rõ ràng hơn."
            
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error in chat_response: {error_detail}")
        return f"Lỗi: {str(e)}\n\nVui lòng thử lại hoặc diễn đạt câu hỏi khác."


# Create Gradio ChatInterface
demo = gr.ChatInterface(
    fn=chat_response,
    title="⚽ Chatbot Bóng Đá Việt Nam",
    description="💬 Hỏi đáp về cầu thủ, huấn luyện viên, câu lạc bộ Việt Nam\n📊 Knowledge Graph: 1,060 nodes | 36,184 relationships | 🤖 LLM + Graph Reasoning"
)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
