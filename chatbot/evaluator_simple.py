"""
Evaluator đơn giản cho chatbot
"""

import json
import logging
import time
from typing import Dict, List
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Evaluator:
    """Đánh giá chatbot trên tập dữ liệu."""
    
    def __init__(self, dataset_path: str):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.questions = json.load(f)
        logger.info(f"Loaded {len(self.questions)} questions")
    
    def evaluate(self, chatbot, max_questions: int = None) -> Dict:
        """
        Đánh giá chatbot.
        
        Args:
            chatbot: Chatbot có method:
                - answer_yes_no(question, statement) -> (answer, confidence)
                - answer_mcq(question, choices) -> (answer, confidence)
        """
        questions = self.questions[:max_questions] if max_questions else self.questions
        
        results = {
            "total": len(questions),
            "correct": 0,
            "by_type": {"yes_no": {"total": 0, "correct": 0}, "mcq": {"total": 0, "correct": 0}},
            "by_hops": {"1": {"total": 0, "correct": 0}, "2": {"total": 0, "correct": 0}},
            "by_answer": {"ĐÚNG": {"total": 0, "correct": 0}, "SAI": {"total": 0, "correct": 0}},
            "errors": []
        }
        
        start = time.time()
        
        for i, q in enumerate(questions):
            if (i + 1) % 200 == 0:
                logger.info(f"Progress: {i+1}/{len(questions)}")
            
            try:
                if q['type'] == 'yes_no':
                    pred, _ = chatbot.answer_yes_no(q['question'])
                    expected = q['answer']
                else:  # mcq
                    pred, _ = chatbot.answer_mcq(q['question'], q['choices'])
                    expected = q['answer']
                
                is_correct = (pred == expected)
                
                # Update stats
                results["by_type"][q['type']]["total"] += 1
                hop_key = str(q.get('hops', 1))
                results["by_hops"][hop_key]["total"] += 1
                
                if q['type'] == 'yes_no':
                    results["by_answer"][expected]["total"] += 1
                
                if is_correct:
                    results["correct"] += 1
                    results["by_type"][q['type']]["correct"] += 1
                    results["by_hops"][hop_key]["correct"] += 1
                    if q['type'] == 'yes_no':
                        results["by_answer"][expected]["correct"] += 1
                else:
                    results["errors"].append({
                        "id": q['id'],
                        "question": q['question'],
                        "expected": expected,
                        "predicted": pred,
                        "type": q['type'],
                        "hops": q.get('hops', 1)
                    })
                    
            except Exception as e:
                logger.error(f"Error on Q{q['id']}: {e}")
                results["errors"].append({"id": q['id'], "error": str(e)})
        
        # Calculate accuracy
        results["accuracy"] = results["correct"] / results["total"] * 100
        
        for t in results["by_type"]:
            total = results["by_type"][t]["total"]
            if total > 0:
                results["by_type"][t]["accuracy"] = results["by_type"][t]["correct"] / total * 100
        
        for h in results["by_hops"]:
            total = results["by_hops"][h]["total"]
            if total > 0:
                results["by_hops"][h]["accuracy"] = results["by_hops"][h]["correct"] / total * 100
        
        for a in results["by_answer"]:
            total = results["by_answer"][a]["total"]
            if total > 0:
                results["by_answer"][a]["accuracy"] = results["by_answer"][a]["correct"] / total * 100
        
        results["elapsed"] = time.time() - start
        results["timestamp"] = datetime.now().isoformat()
        
        return results
    
    def print_results(self, results: Dict):
        """In kết quả."""
        print("\n" + "=" * 50)
        print("📊 KẾT QUẢ ĐÁNH GIÁ")
        print("=" * 50)
        
        print(f"\n✅ Tổng: {results['correct']}/{results['total']}")
        print(f"📈 Độ chính xác: {results['accuracy']:.2f}%")
        
        print("\n--- Theo loại câu hỏi ---")
        for t, s in results["by_type"].items():
            if s["total"] > 0:
                print(f"  {t}: {s['correct']}/{s['total']} ({s.get('accuracy', 0):.2f}%)")
        
        print("\n--- Theo số hop ---")
        for h, s in results["by_hops"].items():
            if s["total"] > 0:
                print(f"  {h}-hop: {s['correct']}/{s['total']} ({s.get('accuracy', 0):.2f}%)")
        
        print("\n--- Theo đáp án (Đúng/Sai) ---")
        for a, s in results["by_answer"].items():
            if s["total"] > 0:
                print(f"  {a}: {s['correct']}/{s['total']} ({s.get('accuracy', 0):.2f}%)")
        
        print(f"\n⏱️ Thời gian: {results['elapsed']:.2f}s")
        
        if results["errors"][:3]:
            print("\n--- Một số lỗi ---")
            for e in results["errors"][:3]:
                print(f"  Q: {e.get('question', '')[:60]}...")
                print(f"     Expected: {e.get('expected')} | Got: {e.get('predicted')}")
    
    def save_results(self, results: Dict, filepath: str):
        """Lưu kết quả."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        save_data = results.copy()
        save_data["errors"] = results["errors"][:50]  # Chỉ lưu 50 lỗi đầu
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {filepath}")


def main():
    from chatbot.graph_chatbot import GraphChatbot
    
    # Khởi tạo chatbot
    chatbot = GraphChatbot()
    if not chatbot.initialize():
        print("Failed to initialize chatbot")
        return
    
    # Đánh giá
    evaluator = Evaluator("data/evaluation/eval_dataset.json")
    results = evaluator.evaluate(chatbot)
    evaluator.print_results(results)
    evaluator.save_results(results, "reports/graph_chatbot_eval.json")


if __name__ == "__main__":
    main()
