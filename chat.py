#!/usr/bin/env python3
"""Interactive chatbot        if user_input.lower() == "help":
            print()
            print("📝 Ví dụ câu hỏi TRUE/FALSE (1-hop):")
            print("  • Nguyễn Quang Hải đã chơi cho Hà Nội.")
            print("  • Đoàn Văn Hậu sinh ra ở Thái Bình.")
            print("  • Nguyễn Công Phượng có quê ở Gia Lai.")
            print("  • Lương Xuân Trường chơi cho HAGL.")
            print("  • Park Hang-seo đã huấn luyện Hà Nội.")
            print()
            print("📝 Ví dụ câu hỏi TRUE/FALSE (2-hop):")
            print("  • Nguyễn Quang Hải và Đoàn Văn Hậu từng chơi cùng câu lạc bộ.")
            print("  • Nguyễn Công Phượng và Lương Xuân Trường cùng quê.")
            print("  • Văn Quyết và Quang Hải vừa cùng CLB vừa cùng quê.")
            print()
            print("📝 Ví dụ câu hỏi MCQ:")
            print("  • Nguyễn Quang Hải đã chơi cho câu lạc bộ nào? | Hà Nội | HAGL | Viettel | Bình Dương")
            print("  • Đoàn Văn Hậu sinh ra ở tỉnh nào? | Hà Nội | Thái Bình | Nghệ An | Gia Lai")
            print("  • Nguyễn Công Phượng chơi cho đội nào? | HAGL | Hà Nội | Viettel | SLNA")
            print()
            print("💡 Lưu ý:")
            print("  • Có thể dùng tên ngắn: 'Quang Hải', 'Văn Hậu', 'Công Phượng'")
            print("  • Dấu cách trước dấu ? không ảnh hưởng")
            print("  • MCQ: Tách câu hỏi và đáp án bằng dấu |")
            print()
            continueamese Football."""

from chatbot.graph_chatbot import GraphReasoningChatbot


def main():
    chatbot = GraphReasoningChatbot()
    chatbot.initialize()
    
    print("=" * 70)
    print("🤖 GRAPHRAG CHATBOT - BÓNG ĐÁ VIỆT NAM")
    print("   Model: GraphReasoningChatbot | Accuracy: 97.23%")
    print("=" * 70)
    print()
    print("📋 Các loại câu hỏi hỗ trợ:")
    print()
    print("🔹 TRUE/FALSE - 1-hop (trả lời Đúng/Sai):")
    print("  • [Cầu thủ] (đã) chơi cho [CLB]")
    print("  • [Cầu thủ] sinh ra ở [Tỉnh] / có quê ở [Tỉnh]")
    print("  • [HLV] (đã) huấn luyện [CLB]")
    print()
    print("🔹 TRUE/FALSE - 2-hop (quan hệ gián tiếp):")
    print("  • [Cầu thủ 1] và [Cầu thủ 2] từng chơi cùng câu lạc bộ")
    print("  • [Cầu thủ 1] và [Cầu thủ 2] cùng quê")
    print("  • [Cầu thủ 1] và [Cầu thủ 2] vừa cùng CLB vừa cùng quê")
    print()
    print("🔹 MCQ (trắc nghiệm - thêm lựa chọn sau dấu |):")
    print("  • [Cầu thủ] (đã) chơi cho câu lạc bộ nào? | A | B | C | D")
    print("  • [Cầu thủ] sinh ra ở tỉnh nào? | A | B | C | D")
    print("  • [HLV] (đã) huấn luyện CLB nào? | A | B | C | D")
    print("  • Ai từng chơi cùng CLB với [Cầu thủ]? | A | B | C | D")
    print()
    print('💡 Gõ "help" để xem ví dụ cụ thể, "quit" để thoát.')
    print("=" * 70)
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
