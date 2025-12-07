#!/usr/bin/env python3
"""Interactive LLM + Graph chatbot for Vietnamese Football."""

import logging
logging.basicConfig(level=logging.WARNING)

from chatbot.llm_chatbot import LLMGraphChatbot


def main():
    print("🚀 Đang tải LLM Qwen2-0.5B + Knowledge Graph...")
    chatbot = LLMGraphChatbot()
    chatbot.initialize()
    
    print()
    print("=" * 60)
    print("🤖 CHATBOT BÓNG ĐÁ VIỆT NAM (LLM + GraphRAG)")
    print("=" * 60)
    print()
    print("💡 Bạn có thể hỏi bằng ngôn ngữ tự nhiên:")
    print("   • Quang Hải có chơi cho Hà Nội không?")
    print("   • Văn Hậu quê ở đâu?")
    print("   • Quang Hải với Văn Hậu cùng đội không?")
    print("   • Công Phượng sinh ra ở Nghệ An đúng không?")
    print()
    print("📝 Hoặc format cố định:")
    print("   • Nguyễn Quang Hải đã chơi cho Hà Nội.")
    print("   • Đoàn Văn Hậu sinh ra ở Thái Bình.")
    print()
    print("🎯 MCQ (thêm lựa chọn sau dấu |):")
    print("   • Quang Hải chơi cho CLB nào? | Hà Nội | HAGL | Viettel | Bình Dương")
    print()
    print('Gõ "quit" để thoát, "help" để xem thêm.')
    print("=" * 60)
    print()
    
    while True:
        try:
            user_input = input("❓ Hỏi: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Tạm biệt!")
            break
            
        if not user_input:
            continue
            
        if user_input.lower() == "quit":
            print("👋 Tạm biệt!")
            break
            
        if user_input.lower() == "help":
            print()
            print("📋 Các loại câu hỏi:")
            print()
            print("1️⃣ CẦU THỦ - CLB:")
            print("   • Quang Hải có chơi cho Hà Nội không?")
            print("   • Công Phượng từng khoác áo HAGL chưa?")
            print()
            print("2️⃣ CẦU THỦ - QUÊ:")
            print("   • Văn Hậu quê ở đâu?")
            print("   • Công Phượng sinh ra ở Nghệ An phải không?")
            print()
            print("3️⃣ HAI CẦU THỦ - CÙNG ĐỘI:")
            print("   • Quang Hải và Văn Hậu cùng đội không?")
            print("   • Ai từng là đồng đội của Công Phượng?")
            print()
            print("4️⃣ HAI CẦU THỦ - CÙNG QUÊ:")
            print("   • Xuân Trường và Văn Toàn cùng quê không?")
            print()
            print("5️⃣ HLV - CLB:")
            print("   • Park Hang-seo huấn luyện đội nào?")
            print()
            continue
        
        # Check if MCQ (contains |)
        if "|" in user_input:
            parts = [p.strip() for p in user_input.split("|")]
            question = parts[0]
            choices = parts[1:]
            
            if len(choices) < 2:
                print("⚠️ MCQ cần ít nhất 2 lựa chọn!")
                print()
                continue
                
            answer, confidence = chatbot.answer_mcq(question, choices)
            print(f"✅ Đáp án: {answer}")
            print(f"📊 Độ tin cậy: {confidence:.0%}")
        else:
            # TRUE/FALSE
            answer, confidence = chatbot.answer_true_false(user_input)
            result = "ĐÚNG ✓" if answer else "SAI ✗"
            print(f"✅ Kết quả: {result}")
            print(f"📊 Độ tin cậy: {confidence:.0%}")
        
        print()


if __name__ == "__main__":
    main()
