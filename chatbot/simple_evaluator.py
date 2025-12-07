"""
Simple Evaluator for Chatbot

Đánh giá chatbot đơn giản với 3 loại câu hỏi:
1. TRUE/FALSE
2. YES/NO
3. MCQ
"""

import json
import logging
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleEvaluator:
    """Đánh giá chatbot trên tập dữ liệu."""
    
    def __init__(self, dataset_path: str):
        """
        Args:
            dataset_path: Đường dẫn đến file JSON chứa câu hỏi
        """
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.questions = json.load(f)
        logger.info(f"Loaded {len(self.questions)} questions")
    
    def evaluate_chatbot(self, chatbot, max_questions: int = None) -> Dict:
        """
        Đánh giá chatbot.
        
        Args:
            chatbot: Chatbot có các method:
                - answer_true_false(question, statement) -> (answer, confidence)
                - answer_yes_no(question) -> (answer, confidence)
                - answer_mcq(question, choices) -> (answer, confidence)
            max_questions: Số câu hỏi tối đa để đánh giá
            
        Returns:
            Dict chứa kết quả đánh giá
        """
        questions = self.questions[:max_questions] if max_questions else self.questions
        
        results = {
            "total": len(questions),
            "correct": 0,
            "wrong": 0,
            "by_type": {
                "true_false": {"total": 0, "correct": 0},
                "yes_no": {"total": 0, "correct": 0},
                "mcq": {"total": 0, "correct": 0}
            },
            "by_category": {},
            "by_hops": {
                "1-hop": {"total": 0, "correct": 0},
                "2-hop": {"total": 0, "correct": 0}
            },
            "errors": []
        }
        
        start_time = time.time()
        
        for i, q in enumerate(questions):
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{len(questions)}")
            
            try:
                predicted = None
                
                if q["type"] == "true_false":
                    pred, conf = chatbot.answer_true_false(q["question"], q["statement"])
                    predicted = pred
                    
                elif q["type"] == "yes_no":
                    pred, conf = chatbot.answer_yes_no(q["question"])
                    predicted = pred
                    
                elif q["type"] == "mcq":
                    pred, conf = chatbot.answer_mcq(q["question"], q["choices"])
                    predicted = pred
                
                # Check correctness
                is_correct = (predicted == q["answer"])
                
                # Update stats
                results["by_type"][q["type"]]["total"] += 1
                
                if is_correct:
                    results["correct"] += 1
                    results["by_type"][q["type"]]["correct"] += 1
                else:
                    results["wrong"] += 1
                    results["errors"].append({
                        "id": q["id"],
                        "type": q["type"],
                        "question": q["question"],
                        "expected": q["answer"],
                        "predicted": predicted,
                        "category": q.get("category")
                    })
                
                # By category
                cat = q.get("category", "unknown")
                if cat not in results["by_category"]:
                    results["by_category"][cat] = {"total": 0, "correct": 0}
                results["by_category"][cat]["total"] += 1
                if is_correct:
                    results["by_category"][cat]["correct"] += 1
                
                # By hops
                hops = q.get("hops", 1)
                hop_key = f"{hops}-hop"
                results["by_hops"][hop_key]["total"] += 1
                if is_correct:
                    results["by_hops"][hop_key]["correct"] += 1
                    
            except Exception as e:
                logger.error(f"Error on question {q['id']}: {e}")
                results["wrong"] += 1
                results["errors"].append({
                    "id": q["id"],
                    "error": str(e)
                })
        
        elapsed = time.time() - start_time
        
        # Calculate percentages
        results["accuracy"] = results["correct"] / results["total"] * 100 if results["total"] > 0 else 0
        
        for qtype in results["by_type"]:
            total = results["by_type"][qtype]["total"]
            correct = results["by_type"][qtype]["correct"]
            results["by_type"][qtype]["accuracy"] = correct / total * 100 if total > 0 else 0
        
        for cat in results["by_category"]:
            total = results["by_category"][cat]["total"]
            correct = results["by_category"][cat]["correct"]
            results["by_category"][cat]["accuracy"] = correct / total * 100 if total > 0 else 0
        
        for hop in results["by_hops"]:
            total = results["by_hops"][hop]["total"]
            correct = results["by_hops"][hop]["correct"]
            results["by_hops"][hop]["accuracy"] = correct / total * 100 if total > 0 else 0
        
        results["elapsed_seconds"] = elapsed
        results["timestamp"] = datetime.now().isoformat()
        
        return results
    
    def print_results(self, results: Dict):
        """In kết quả đánh giá."""
        print("\n" + "=" * 60)
        print("📊 KẾT QUẢ ĐÁNH GIÁ CHATBOT")
        print("=" * 60)
        
        print(f"\n✅ Tổng số câu hỏi: {results['total']}")
        print(f"✅ Trả lời đúng: {results['correct']}")
        print(f"❌ Trả lời sai: {results['wrong']}")
        print(f"📈 Độ chính xác: {results['accuracy']:.2f}%")
        
        print("\n--- Theo loại câu hỏi ---")
        for qtype, stats in results["by_type"].items():
            if stats["total"] > 0:
                print(f"  {qtype}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.2f}%)")
        
        print("\n--- Theo số hop ---")
        for hop, stats in results["by_hops"].items():
            if stats["total"] > 0:
                print(f"  {hop}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.2f}%)")
        
        print("\n--- Theo danh mục ---")
        for cat, stats in sorted(results["by_category"].items()):
            if stats["total"] > 0:
                print(f"  {cat}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.2f}%)")
        
        print(f"\n⏱️ Thời gian: {results['elapsed_seconds']:.2f}s")
        
        if results["errors"][:5]:
            print("\n--- Một số lỗi mẫu ---")
            for err in results["errors"][:5]:
                print(f"  Q: {err.get('question', 'N/A')[:80]}...")
                print(f"     Expected: {err.get('expected')} | Got: {err.get('predicted')}")
                print()
    
    def save_results(self, results: Dict, filepath: str):
        """Lưu kết quả ra file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Only save first 100 errors to keep file size manageable
        results_to_save = results.copy()
        results_to_save["errors"] = results["errors"][:100]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_to_save, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved results to {filepath}")


def evaluate_simple_chatbot():
    """Đánh giá SimpleKGChatbot."""
    from chatbot.simple_chatbot import SimpleKGChatbot
    
    chatbot = SimpleKGChatbot()
    if not chatbot.initialize():
        print("Failed to initialize chatbot")
        return
    
    evaluator = SimpleEvaluator("data/evaluation/simple_eval_dataset.json")
    results = evaluator.evaluate_chatbot(chatbot)
    evaluator.print_results(results)
    evaluator.save_results(results, "reports/simple_chatbot_eval.json")


def evaluate_with_gemini():
    """Đánh giá với Gemini API."""
    import google.generativeai as genai
    import os
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set")
        return
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    class GeminiWrapper:
        def __init__(self, model):
            self.model = model
        
        def answer_true_false(self, question: str, statement: str) -> Tuple[str, float]:
            prompt = f"""Bạn là chuyên gia về bóng đá Việt Nam.
Hãy trả lời câu hỏi sau bằng TRUE hoặc FALSE.
Chỉ trả lời TRUE hoặc FALSE, không giải thích.

Câu hỏi: {question}
Mệnh đề: {statement}

Trả lời:"""
            try:
                response = self.model.generate_content(prompt)
                answer = response.text.strip().upper()
                if "TRUE" in answer:
                    return "TRUE", 1.0
                return "FALSE", 1.0
            except Exception as e:
                logger.error(f"Gemini error: {e}")
                return "FALSE", 0.5
        
        def answer_yes_no(self, question: str) -> Tuple[str, float]:
            prompt = f"""Bạn là chuyên gia về bóng đá Việt Nam.
Hãy trả lời câu hỏi sau bằng YES hoặc NO.
Chỉ trả lời YES hoặc NO, không giải thích.

Câu hỏi: {question}

Trả lời:"""
            try:
                response = self.model.generate_content(prompt)
                answer = response.text.strip().upper()
                if "YES" in answer or "CÓ" in answer.upper():
                    return "YES", 1.0
                return "NO", 1.0
            except Exception as e:
                logger.error(f"Gemini error: {e}")
                return "NO", 0.5
        
        def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float]:
            choices_text = "\n".join([f"{chr(65+i)}. {c}" for i, c in enumerate(choices)])
            prompt = f"""Bạn là chuyên gia về bóng đá Việt Nam.
Hãy chọn đáp án đúng cho câu hỏi trắc nghiệm sau.
Chỉ trả lời bằng nội dung đáp án (không cần A, B, C, D).

Câu hỏi: {question}
{choices_text}

Đáp án đúng là:"""
            try:
                response = self.model.generate_content(prompt)
                answer = response.text.strip()
                
                # Tìm đáp án khớp nhất
                for choice in choices:
                    if choice.lower() in answer.lower() or answer.lower() in choice.lower():
                        return choice, 1.0
                
                # Kiểm tra theo chữ cái
                for i, choice in enumerate(choices):
                    if chr(65+i) in answer.upper():
                        return choice, 1.0
                
                return choices[0], 0.3
            except Exception as e:
                logger.error(f"Gemini error: {e}")
                return choices[0], 0.3
    
    gemini = GeminiWrapper(model)
    
    evaluator = SimpleEvaluator("data/evaluation/simple_eval_dataset.json")
    # Chỉ test 500 câu để tránh rate limit
    results = evaluator.evaluate_chatbot(gemini, max_questions=500)
    evaluator.print_results(results)
    evaluator.save_results(results, "reports/gemini_eval.json")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--gemini":
        evaluate_with_gemini()
    else:
        evaluate_simple_chatbot()
