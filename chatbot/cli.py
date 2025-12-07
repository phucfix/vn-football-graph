#!/usr/bin/env python3
"""
Command-line interface for Vietnamese Football Chatbot.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Run interactive chatbot in terminal."""
    print("=" * 60)
    print("🤖 Vietnamese Football Chatbot - CLI")
    print("=" * 60)
    
    # Ask which chatbot to use
    print("\nChọn loại chatbot:")
    print("1. SimpleChatbot (Graph Reasoning - nhanh, không cần GPU)")
    print("2. HybridChatbot (Graph + LLM formatting - cần GPU/thời gian load)")
    
    choice = input("\nNhập 1 hoặc 2 [mặc định: 1]: ").strip()
    
    if choice == "2":
        print("\n⏳ Đang khởi tạo HybridChatbot (có thể mất vài phút)...")
        from chatbot.chatbot import HybridChatbot
        chatbot = HybridChatbot()
        if not chatbot.initialize():
            print("❌ Không thể khởi tạo HybridChatbot!")
            return
        print("✅ HybridChatbot sẵn sàng!")
        chatbot_name = "HybridChatbot"
    else:
        print("\n⏳ Đang khởi tạo SimpleChatbot...")
        from chatbot.chatbot import SimpleChatbot
        chatbot = SimpleChatbot()
        if not chatbot.initialize():
            print("❌ Không thể khởi tạo SimpleChatbot!")
            return
        print("✅ SimpleChatbot sẵn sàng!")
        chatbot_name = "SimpleChatbot"
    
    print("\n" + "=" * 60)
    print(f"💬 {chatbot_name} - Sẵn sàng trả lời!")
    print("Gõ 'quit' hoặc 'exit' để thoát")
    print("Gõ 'help' để xem hướng dẫn")
    print("=" * 60 + "\n")
    
    while True:
        try:
            question = input("👤 Bạn: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['quit', 'exit', 'q', 'thoát']:
                print("\n👋 Tạm biệt!")
                break
                
            if question.lower() == 'help':
                print_help()
                continue
            
            # Get answer
            print("🤔 Đang xử lý...")
            answer = chatbot.chat(question)
            print(f"🤖 Bot: {answer}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"❌ Lỗi: {e}\n")


def print_help():
    """Print help information."""
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    📖 HƯỚNG DẪN SỬ DỤNG                      ║
╠══════════════════════════════════════════════════════════════╣
║ Các loại câu hỏi hỗ trợ:                                     ║
║                                                              ║
║ 1️⃣  Câu hỏi Có/Không:                                        ║
║     • "Quang Hải có thi đấu cho Hà Nội FC không?"            ║
║     • "Công Phượng sinh ra ở Nghệ An phải không?"            ║
║                                                              ║
║ 2️⃣  Câu hỏi về thông tin:                                    ║
║     • "Quang Hải chơi ở vị trí nào?"                         ║
║     • "Ai là huấn luyện viên của đội tuyển Việt Nam?"        ║
║     • "Công Phượng đã từng thi đấu cho những câu lạc bộ nào?"║
║                                                              ║
║ 3️⃣  Câu hỏi về mối quan hệ:                                  ║
║     • "Quang Hải và Văn Hậu có cùng đội không?"              ║
║     • "Văn Toàn và Xuân Trường có cùng quê không?"           ║
║                                                              ║
║ 4️⃣  Câu hỏi liệt kê:                                         ║
║     • "Liệt kê các cầu thủ của Hà Nội FC"                    ║
║     • "Những cầu thủ nào sinh ra ở Thanh Hóa?"               ║
║                                                              ║
║ ⚠️  Hạn chế:                                                  ║
║     • Chỉ có dữ liệu về bóng đá Việt Nam từ Wikipedia        ║
║     • Không có số liệu thống kê (bàn thắng, số trận)         ║
║     • Dữ liệu có thể không được cập nhật mới nhất            ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(help_text)


if __name__ == "__main__":
    main()
