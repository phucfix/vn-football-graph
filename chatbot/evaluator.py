"""
Evaluator cho Vietnamese Football Chatbot
"""

import json
import logging
import time
from typing import Dict
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Evaluator:
    """Đánh giá chatbot."""
    
    def __init__(self, dataset_path: str):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.questions = json.load(f)
        logger.info(f"Loaded {len(self.questions)} questions")
    
    def evaluate(self, chatbot, max_questions: int = None) -> Dict:
        """Đánh giá chatbot."""
        questions = self.questions[:max_questions] if max_questions else self.questions
        
        results = {
            "total": len(questions),
            "correct": 0,
            "wrong": 0,
            "by_type": {"true_false": {"total": 0, "correct": 0}, "mcq": {"total": 0, "correct": 0}},
            "by_hops": {"1": {"total": 0, "correct": 0}, "2": {"total": 0, "correct": 0}, "3": {"total": 0, "correct": 0}},
            "by_category": {},
            "errors": []
        }
        
        start = time.time()
        
        for i, q in enumerate(questions):
            if (i + 1) % 200 == 0:
                logger.info(f"Progress: {i+1}/{len(questions)}")
            
            try:
                if q['type'] == 'true_false':
                    predicted, conf = chatbot.answer_true_false(q['question'])
                    expected = q['answer']
                    is_correct = (predicted == expected)
                    
                elif q['type'] == 'mcq':
                    predicted, conf = chatbot.answer_mcq(q['question'], q['choices'])
                    expected = q['answer']
                    is_correct = (predicted == expected)
                else:
                    continue
                
                results['by_type'][q['type']]['total'] += 1
                hop = str(q.get('hops', 1))
                results['by_hops'][hop]['total'] += 1
                
                cat = q.get('category', 'unknown')
                if cat not in results['by_category']:
                    results['by_category'][cat] = {"total": 0, "correct": 0}
                results['by_category'][cat]['total'] += 1
                
                if is_correct:
                    results['correct'] += 1
                    results['by_type'][q['type']]['correct'] += 1
                    results['by_hops'][hop]['correct'] += 1
                    results['by_category'][cat]['correct'] += 1
                else:
                    results['wrong'] += 1
                    results['errors'].append({
                        "id": q['id'],
                        "question": q['question'],
                        "expected": expected,
                        "predicted": predicted,
                        "category": cat
                    })
                    
            except Exception as e:
                logger.error(f"Error on Q{q['id']}: {e}")
                results['wrong'] += 1
        
        elapsed = time.time() - start
        
        # Calculate accuracy
        results['accuracy'] = results['correct'] / results['total'] * 100 if results['total'] > 0 else 0
        
        for t in results['by_type']:
            total = results['by_type'][t]['total']
            correct = results['by_type'][t]['correct']
            results['by_type'][t]['accuracy'] = correct / total * 100 if total > 0 else 0
        
        for h in results['by_hops']:
            total = results['by_hops'][h]['total']
            correct = results['by_hops'][h]['correct']
            results['by_hops'][h]['accuracy'] = correct / total * 100 if total > 0 else 0
        
        for c in results['by_category']:
            total = results['by_category'][c]['total']
            correct = results['by_category'][c]['correct']
            results['by_category'][c]['accuracy'] = correct / total * 100 if total > 0 else 0
        
        results['elapsed_seconds'] = elapsed
        results['timestamp'] = datetime.now().isoformat()
        
        return results
    
    def print_results(self, results: Dict):
        """In kết quả."""
        print("\n" + "=" * 60)
        print("📊 KẾT QUẢ ĐÁNH GIÁ")
        print("=" * 60)
        
        print(f"\n📈 Tổng: {results['correct']}/{results['total']} ({results['accuracy']:.2f}%)")
        
        print("\n--- Theo loại câu hỏi ---")
        for t, s in results['by_type'].items():
            if s['total'] > 0:
                print(f"  {t}: {s['correct']}/{s['total']} ({s['accuracy']:.2f}%)")
        
        print("\n--- Theo số hop ---")
        for h, s in sorted(results['by_hops'].items()):
            if s['total'] > 0:
                print(f"  {h}-hop: {s['correct']}/{s['total']} ({s['accuracy']:.2f}%)")
        
        print("\n--- Theo category ---")
        for c, s in sorted(results['by_category'].items()):
            if s['total'] > 0:
                print(f"  {c}: {s['correct']}/{s['total']} ({s['accuracy']:.2f}%)")
        
        print(f"\n⏱️ Thời gian: {results['elapsed_seconds']:.2f}s")
        
        if results['errors'][:5]:
            print("\n--- Lỗi mẫu ---")
            for e in results['errors'][:5]:
                print(f"  Q: {e['question'][:60]}...")
                print(f"     Expected: {e['expected']}, Got: {e['predicted']}")
    
    def save_results(self, results: Dict, filepath: str):
        """Lưu kết quả."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        to_save = results.copy()
        to_save['errors'] = results['errors'][:50]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {filepath}")


def main():
    from chatbot.graph_chatbot import GraphReasoningChatbot
    
    chatbot = GraphReasoningChatbot()
    if not chatbot.initialize():
        print("Failed to initialize")
        return
    
    evaluator = Evaluator("data/evaluation/eval_dataset.json")
    results = evaluator.evaluate(chatbot)
    evaluator.print_results(results)
    evaluator.save_results(results, "reports/chatbot_eval.json")


if __name__ == "__main__":
    main()
