#!/usr/bin/env python3
"""
Đánh giá chỉ GraphRAG chatbot (không so sánh với Gemini)
"""

import json
import logging
from pathlib import Path
from chatbot.llm_chatbot import LLMGraphChatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_questions(limit=None):
    """Load questions from dataset"""
    questions_file = Path("data/evaluation/evaluation_questions.json")
    with open(questions_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    if limit:
        questions = questions[:limit]
    
    return questions

def evaluate_graphrag(questions):
    """Evaluate GraphRAG chatbot"""
    logger.info("🚀 Khởi tạo GraphRAG Chatbot...")
    chatbot = LLMGraphChatbot()
    
    correct = 0
    total = len(questions)
    results = []
    
    for i, item in enumerate(questions):
        question = item["question_vi"]  # Sử dụng câu hỏi tiếng Việt
        correct_answer = item["correct_answer"]
        question_type = item["question_type"]
        
        try:
            if question_type == "true_false":
                answer, confidence = chatbot.answer_true_false(question)
                is_correct = answer == correct_answer
            else:  # multiple_choice
                answer, confidence = chatbot.answer_mcq(question, item["options"])
                is_correct = answer == correct_answer
            
            if is_correct:
                correct += 1
            
            results.append({
                "question": question,
                "type": question_type,
                "correct_answer": correct_answer,
                "predicted_answer": answer,
                "confidence": confidence,
                "correct": is_correct
            })
            
            # Progress
            if (i + 1) % 20 == 0:
                accuracy = correct / (i + 1) * 100
                logger.info(f"Progress: {i+1}/{total} - Accuracy: {accuracy:.2f}%")
                
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
    mcq_questions = [r for r in results if r["type"] == "multiple_choice"]
    
    tf_correct = sum(1 for r in tf_questions if r["correct"])
    mcq_correct = sum(1 for r in mcq_questions if r["correct"])
    
    tf_accuracy = tf_correct / len(tf_questions) * 100 if tf_questions else 0
    mcq_accuracy = mcq_correct / len(mcq_questions) * 100 if mcq_questions else 0
    
    # Breakdown by hop count
    hop1_questions = [r for r in results if "1-hop" in r["question"].lower()]
    hop2_questions = [r for r in results if "2-hop" in r["question"].lower()]
    hop3_questions = [r for r in results if "3-hop" in r["question"].lower()]
    
    hop1_accuracy = sum(1 for r in hop1_questions if r["correct"]) / len(hop1_questions) * 100 if hop1_questions else 0
    hop2_accuracy = sum(1 for r in hop2_questions if r["correct"]) / len(hop2_questions) * 100 if hop2_questions else 0
    hop3_accuracy = sum(1 for r in hop3_questions if r["correct"]) / len(hop3_questions) * 100 if hop3_questions else 0
    
    print("\n" + "="*60)
    print("📊 KẾT QUẢ ĐÁNH GIÁ GRAPHRAG CHATBOT")
    print("="*60)
    print(f"📈 Tổng thể: {correct}/{total} = {accuracy:.2f}%")
    print(f"🔸 True/False: {tf_correct}/{len(tf_questions)} = {tf_accuracy:.2f}%")
    print(f"🔸 Multiple Choice: {mcq_correct}/{len(mcq_questions)} = {mcq_accuracy:.2f}%")
    print()
    print("📊 Theo độ phức tạp:")
    if hop1_questions:
        print(f"🔸 1-hop: {sum(1 for r in hop1_questions if r['correct'])}/{len(hop1_questions)} = {hop1_accuracy:.2f}%")
    if hop2_questions:
        print(f"🔸 2-hop: {sum(1 for r in hop2_questions if r['correct'])}/{len(hop2_questions)} = {hop2_accuracy:.2f}%")
    if hop3_questions:
        print(f"🔸 3-hop: {sum(1 for r in hop3_questions if r['correct'])}/{len(hop3_questions)} = {hop3_accuracy:.2f}%")
    print("="*60)
    
    return {
        "total_accuracy": accuracy,
        "tf_accuracy": tf_accuracy,
        "mcq_accuracy": mcq_accuracy,
        "hop1_accuracy": hop1_accuracy,
        "hop2_accuracy": hop2_accuracy,
        "hop3_accuracy": hop3_accuracy,
        "results": results
    }

def main():
    questions = load_questions(limit=200)  # Test với 200 câu
    logger.info(f"Loaded {len(questions)} questions")
    
    results = evaluate_graphrag(questions)
    
    # Save results
    output_file = "graphrag_evaluation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Results saved to {output_file}")

if __name__ == "__main__":
    main()
