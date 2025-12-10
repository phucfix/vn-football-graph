"""Quick test after manual fix"""
from chatbot.chatbot import HybridChatbot

print("=" * 70)
print("TESTING CHATBOT AFTER MANUAL FIX")
print("=" * 70)

chatbot = HybridChatbot()

test_questions = [
    "Công Phượng có chơi cho HAGL không?",
    "Quang Hải chơi cho câu lạc bộ nào?",
    "Công Phượng và Văn Toàn có từng chơi cùng câu lạc bộ không?",
    "Cho tôi biết Công Phượng chơi cho đội nào?",
]

for i, question in enumerate(test_questions, 1):
    print(f"\n{'='*70}")
    print(f"Q{i}: {question}")
    print(f"{'='*70}")
    
    response = chatbot.chat(question)
    print(f"A: {response}")

chatbot.kg.close()
