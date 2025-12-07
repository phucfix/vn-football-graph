#!/usr/bin/env python3
"""
Đánh giá GraphRAG chatbot với các câu hỏi test đơn giản
"""

import json
import logging
from chatbot.llm_chatbot import LLMGraphChatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_questions():
    """Test với các câu hỏi đơn giản để validate system"""
    
    # Test questions giống như đã test trước đây
    test_questions = [
        # True/False questions
        {
            "question": "Nguyễn Quang Hải có chơi cho Hà Nội không?",
            "type": "true_false", 
            "answer": True
        },
        {
            "question": "Công Phượng có chơi cho HAGL không?",
            "type": "true_false",
            "answer": True
        },
        {
            "question": "Văn Hậu có chơi cho Hà Nội không?",
            "type": "true_false", 
            "answer": True
        },
        {
            "question": "Quang Hải có chơi cho HAGL không?",
            "type": "true_false",
            "answer": False
        },
        {
            "question": "Công Phượng có chơi cho Nam Định không?",
            "type": "true_false",
            "answer": False
        },
        
        # MCQ questions
        {
            "question": "Quang Hải chơi cho đội nào?",
            "type": "mcq",
            "options": ["A. Hà Nội", "B. HAGL", "C. Nam Định", "D. Viettel"],
            "answer": "A"
        },
        {
            "question": "Công Phượng chơi cho đội nào?", 
            "type": "mcq",
            "options": ["A. Hà Nội", "B. HAGL", "C. Nam Định", "D. Viettel"],
            "answer": "B"
        },
        {
            "question": "HAGL có trụ sở ở đâu?",
            "type": "mcq", 
            "options": ["A. Hà Nội", "B. Gia Lai", "C. Nam Định", "D. TP.HCM"],
            "answer": "B"
        },
        {
            "question": "Hà Nội FC có trụ sở ở đâu?",
            "type": "mcq",
            "options": ["A. Hà Nội", "B. Gia Lai", "C. Nam Định", "D. TP.HCM"],
            "answer": "A"
        },
        {
            "question": "Công Phượng và Văn Hậu có cùng quê không?",
            "type": "mcq",
            "options": ["A. Có", "B. Không", "C. Không rõ", "D. Chưa có thông tin"],
            "answer": "B"
        }
    ]
    
    return test_questions

def evaluate_graphrag():
    """Evaluate GraphRAG chatbot với test questions"""
    logger.info("🚀 Khởi tạo GraphRAG Chatbot...")
    chatbot = LLMGraphChatbot()
    chatbot.initialize()  # Quan trọng: phải gọi initialize()!
    
    questions = test_simple_questions()
    correct = 0
    total = len(questions)
    results = []
    
    for i, item in enumerate(questions):
        question = item["question"]
        correct_answer = item["answer"]
        question_type = item["type"]
        
        try:
            if question_type == "true_false":
                answer, confidence = chatbot.answer_true_false(question)
                is_correct = answer == correct_answer
                logger.info(f"Q: {question}")
                logger.info(f"Expected: {correct_answer}, Got: {answer}, Confidence: {confidence:.2f}")
            else:  # mcq
                options = item["options"]
                answer, confidence = chatbot.answer_mcq(question, options)
                
                # So sánh với chữ cái đầu tiên của answer  
                answer_letter = answer[0] if answer else ""
                is_correct = answer_letter == correct_answer
                
                logger.info(f"Q: {question}")
                logger.info(f"Options: {options}")
                logger.info(f"Expected: {correct_answer}, Got: {answer} (letter: {answer_letter}), Confidence: {confidence:.2f}")
            
            if is_correct:
                correct += 1
                logger.info("✅ Correct")
            else:
                logger.info("❌ Wrong")
            
            results.append({
                "question": question,
                "type": question_type,
                "correct_answer": correct_answer,
                "predicted_answer": answer,
                "confidence": confidence,
                "correct": is_correct
            })
            
            logger.info("-" * 50)
                
        except Exception as e:
            logger.error(f"Error on question {i+1}: {e}")
            results.append({
                "question": question,
                "type": question_type,
                "correct_answer": correct_answer,
                "predicted_answer": "ERROR",
                "confidence": 0.0,
                "correct": False
            })
    
    # Final results
    accuracy = correct / total * 100
    
    # Breakdown by question type
    tf_questions = [r for r in results if r["type"] == "true_false"]
    mcq_questions = [r for r in results if r["type"] == "mcq"]
    
    tf_correct = sum(1 for r in tf_questions if r["correct"])
    mcq_correct = sum(1 for r in mcq_questions if r["correct"])
    
    tf_accuracy = tf_correct / len(tf_questions) * 100 if tf_questions else 0
    mcq_accuracy = mcq_correct / len(mcq_questions) * 100 if mcq_questions else 0
    
    print("\n" + "="*60)
    print("📊 KẾT QUẢ TEST GRAPHRAG CHATBOT")
    print("="*60)
    print(f"📈 Tổng thể: {correct}/{total} = {accuracy:.2f}%")
    print(f"🔸 True/False: {tf_correct}/{len(tf_questions)} = {tf_accuracy:.2f}%")
    print(f"🔸 Multiple Choice: {mcq_correct}/{len(mcq_questions)} = {mcq_accuracy:.2f}%")
    print("="*60)
    
    return {
        "total_accuracy": accuracy,
        "tf_accuracy": tf_accuracy,
        "mcq_accuracy": mcq_accuracy,
        "results": results
    }

def main():
    results = evaluate_graphrag()
    
    # Save results
    output_file = "simple_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Results saved to {output_file}")

if __name__ == "__main__":
    main()
