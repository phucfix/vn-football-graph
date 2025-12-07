#!/usr/bin/env python3
"""Interactive chatbot for Vietnamese Football."""

from chatbot.graph_chatbot import GraphReasoningChatbot


def main():
    chatbot = GraphReasoningChatbot()
    chatbot.initialize()
    
    print("=" * 60)
    print("🤖 CHATBOT BÓNG ĐÁ VIỆT NAM")
    print("=" * 60)
    print()
    print("📋 Các loại câu hỏi hỗ trợ:")
    print()
    print("TRUE/FALSE (trả lời Đúng/Sai):")
    print("  • [Cầu thủ] đã chơi cho [CLB].")
    print("  • [Cầu thủ] sinh ra ở [Tỉnh].")
    print("  • [HLV] đã huấn luyện [CLB].")
    print("  • [Cầu thủ 1] và [Cầu thủ 2] từng chơi cùng câu lạc bộ.")
    print("  • [Cầu thủ 1] và [Cầu thủ 2] cùng quê.")
    print()
    print("MCQ (trắc nghiệm - thêm các lựa chọn cách nhau bởi |):")
    print("  • [Cầu thủ] đã chơi cho câu lạc bộ nào? | A | B | C | D")
    print("  • [Cầu thủ] sinh ra ở tỉnh nào? | A | B | C | D")
    print()
    print('Gõ "quit" để thoát, "help" để xem ví dụ.')
    print("=" * 60)
    print()
    
    while True:
        try:
            user_input = input("❓ Câu hỏi: ").strip()
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
            print("📝 Ví dụ câu hỏi:")
            print("  • Nguyễn Quang Hải đã chơi cho Hà Nội.")
            print("  • Đoàn Văn Hậu sinh ra ở Thái Bình.")
            print("  • Nguyễn Quang Hải và Đoàn Văn Hậu từng chơi cùng câu lạc bộ.")
            print("  • Park Hang-seo đã huấn luyện Hà Nội.")
            print("  • Nguyễn Quang Hải đã chơi cho câu lạc bộ nào? | Hà Nội | HAGL | Viettel | Bình Dương")
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
