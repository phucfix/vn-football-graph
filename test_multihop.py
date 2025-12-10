#!/usr/bin/env python3
"""
Test multi-hop questions with chatbot
"""

import logging
logging.basicConfig(level=logging.WARNING)

from chatbot.llm_chatbot import LLMGraphChatbot

def test_multihop():
    print("Khởi tạo chatbot...")
    cb = LLMGraphChatbot()
    cb.initialize()
    
    print("\n" + "="*60)
    print("TEST MULTI-HOP QUESTIONS")
    print("="*60)
    
    # 1-HOP QUESTIONS
    print("\n### 1-HOP QUESTIONS (Trực tiếp)")
    print("-" * 60)
    
    tests_1hop = [
        "Quang Hải chơi cho Hà Nội",
        "Công Phượng sinh ra ở Nghệ An",
        "Văn Hậu quê ở Thái Bình"
    ]
    
    for q in tests_1hop:
        ans, conf = cb.answer_true_false(q)
        result = "ĐÚNG" if ans else "SAI"
        print(f"\nQ: {q}")
        print(f"A: {result} (tin cậy: {conf:.0%})")
    
    # 2-HOP QUESTIONS
    print("\n\n### 2-HOP QUESTIONS (1 node trung gian)")
    print("-" * 60)
    
    tests_2hop = [
        ("Quang Hải và Văn Hậu từng cùng đội", "Same Club"),
        ("Công Phượng và Văn Toàn cùng quê", "Same Province"),
        ("Quang Hải và Văn Quyết cùng chơi cho một câu lạc bộ", "Same Club"),
    ]
    
    for q, pattern in tests_2hop:
        ans, conf = cb.answer_true_false(q)
        result = "ĐÚNG" if ans else "SAI"
        print(f"\nQ: {q}")
        print(f"   Pattern: {pattern}")
        print(f"A: {result} (tin cậy: {conf:.0%})")
    
    # 3-HOP QUESTIONS (Complex)
    print("\n\n### 3-HOP QUESTIONS (2 nodes trung gian)")
    print("-" * 60)
    print("(Lưu ý: 3-hop khó hơn, accuracy có thể thấp hơn)\n")
    
    # These might not work perfectly due to complexity
    tests_3hop = [
        "Quang Hải có đồng đội quê Nghệ An không",
        "Người cùng quê Công Phượng có chơi cho HAGL không",
    ]
    
    for q in tests_3hop:
        ans, conf = cb.answer_true_false(q)
        result = "ĐÚNG" if ans else "SAI"
        print(f"\nQ: {q}")
        print(f"A: {result} (tin cậy: {conf:.0%})")
        print("   (Lưu ý: Câu này phức tạp, chatbot có thể chưa parse được)")
    
    # MCQ TESTS
    print("\n\n### MCQ TESTS (Multi-hop reasoning)")
    print("-" * 60)
    
    mcq_tests = [
        ("Quang Hải chơi cho CLB nào?", ["Hà Nội", "HAGL", "Viettel", "Bình Dương"]),
        ("Công Phượng quê ở đâu?", ["Hà Nội", "Nghệ An", "Thái Bình", "TP.HCM"]),
    ]
    
    for q, choices in mcq_tests:
        ans, conf = cb.answer_mcq(q, choices)
        print(f"\nQ: {q}")
        print(f"   Choices: {', '.join(choices)}")
        print(f"A: {ans} (tin cậy: {conf:.0%})")
    
    print("\n" + "="*60)
    print("TEST HOÀN TẤT")
    print("="*60)

if __name__ == "__main__":
    test_multihop()
