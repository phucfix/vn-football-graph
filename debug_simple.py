#!/usr/bin/env python3
"""
Debug câu hỏi đơn giản
"""

from chatbot.llm_chatbot import LLMGraphChatbot
import logging

logging.basicConfig(level=logging.DEBUG)

def debug_single_question():
    chatbot = LLMGraphChatbot()
    chatbot.initialize()
    
    # Test 1 câu đơn giản
    question = "Nguyễn Quang Hải có chơi cho Hà Nội không?"
    print(f"📝 Question: {question}")
    
    # Debug tìm player và club
    player = chatbot.graph_chatbot._find_player(question)
    club = chatbot.graph_chatbot._find_club(question)
    
    print(f"🔍 Found player: {player}")
    print(f"🔍 Found club: {club}")
    
    if player and club:
        result = chatbot.graph_chatbot.check_player_club(player, club)
        print(f"✅ Player-Club check: {result}")
    
    # Test answer
    answer, conf = chatbot.answer_true_false(question)
    print(f"📊 Answer: {answer}, Confidence: {conf}")

if __name__ == "__main__":
    debug_single_question()
