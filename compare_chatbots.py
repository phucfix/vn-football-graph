"""
So sánh GraphRAG Chatbot với Gemini trên dataset đánh giá.
"""

import json
import time
import logging
import os
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiChatbot:
    """Wrapper cho Gemini API."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        self.retry_delay = 2  # Start with 2 seconds
        
    def _call_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini API with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                self.retry_delay = 2  # Reset on success
                return response.text.strip()
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    # Rate limited - wait and retry
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    self.retry_delay = min(self.retry_delay * 2, 60)
                else:
                    raise e
        return ""
        
    def answer_true_false(self, statement: str) -> Tuple[bool, float]:
        """Trả lời câu hỏi TRUE/FALSE."""
        prompt = f"""Bạn là chuyên gia về bóng đá Việt Nam. 
Hãy xác định câu sau ĐÚNG hay SAI dựa trên kiến thức của bạn về bóng đá Việt Nam.

Câu hỏi: "{statement}"

CHỈ trả lời một từ duy nhất: ĐÚNG hoặc SAI"""

        try:
            answer_text = self._call_with_retry(prompt).upper()
            
            if "ĐÚNG" in answer_text or "TRUE" in answer_text or "YES" in answer_text:
                return True, 1.0
            else:
                return False, 1.0
        except Exception as e:
            logger.warning(f"Gemini error: {e}")
            return False, 0.5
    
    def answer_mcq(self, question: str, choices: List[str]) -> Tuple[str, float]:
        """Trả lời câu hỏi MCQ."""
        choices_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(choices)])
        
        prompt = f"""Bạn là chuyên gia về bóng đá Việt Nam.
Hãy chọn đáp án đúng nhất cho câu hỏi sau:

Câu hỏi: {question}

Các lựa chọn:
{choices_text}

CHỈ trả lời số thứ tự của đáp án đúng (1, 2, 3, hoặc 4)."""

        try:
            answer_text = self._call_with_retry(prompt)
            
            # Tìm số trong response
            for i, choice in enumerate(choices):
                if str(i+1) in answer_text or choice.lower() in answer_text.lower():
                    return choice, 1.0
            
            # Default: chọn đáp án đầu tiên
            return choices[0], 0.5
        except Exception as e:
            logger.warning(f"Gemini error: {e}")
            return choices[0], 0.5


class ComparisonEvaluator:
    """So sánh 2 chatbot trên cùng dataset."""
    
    def __init__(self, dataset_path: str):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.dataset = json.load(f)
        logger.info(f"Loaded {len(self.dataset)} questions")
    
    def evaluate_chatbot(self, chatbot, name: str, limit: int = None) -> Dict[str, Any]:
        """Đánh giá một chatbot."""
        results = {
            "name": name,
            "total": 0,
            "correct": 0,
            "by_type": {},
            "by_hops": {},
            "by_category": {},
            "errors": [],
            "time": 0
        }
        
        dataset = self.dataset[:limit] if limit else self.dataset
        start_time = time.time()
        
        for i, item in enumerate(dataset):
            q_type = item["type"]
            category = item.get("category", "unknown")
            hops = item.get("hops", 1)
            
            # Khởi tạo counters
            if q_type not in results["by_type"]:
                results["by_type"][q_type] = {"correct": 0, "total": 0}
            if hops not in results["by_hops"]:
                results["by_hops"][hops] = {"correct": 0, "total": 0}
            if category not in results["by_category"]:
                results["by_category"][category] = {"correct": 0, "total": 0}
            
            results["total"] += 1
            results["by_type"][q_type]["total"] += 1
            results["by_hops"][hops]["total"] += 1
            results["by_category"][category]["total"] += 1
            
            # Lấy câu trả lời
            try:
                if q_type == "true_false":
                    answer, conf = chatbot.answer_true_false(item["question"])
                    expected = item["answer"]
                    is_correct = answer == expected
                else:  # mcq
                    answer, conf = chatbot.answer_mcq(item["question"], item["choices"])
                    expected = item["answer"]
                    is_correct = answer == expected
                
                if is_correct:
                    results["correct"] += 1
                    results["by_type"][q_type]["correct"] += 1
                    results["by_hops"][hops]["correct"] += 1
                    results["by_category"][category]["correct"] += 1
                else:
                    if len(results["errors"]) < 10:
                        results["errors"].append({
                            "question": item["question"][:80],
                            "expected": expected,
                            "got": answer
                        })
            except Exception as e:
                logger.warning(f"Error: {e}")
            
            # Progress
            if (i + 1) % 100 == 0:
                logger.info(f"[{name}] Progress: {i+1}/{len(dataset)}")
            
            # Rate limiting cho Gemini - tăng delay để tránh rate limit
            if "Gemini" in name:
                time.sleep(2.0)  # 30 requests/minute để an toàn
        
        results["time"] = time.time() - start_time
        results["accuracy"] = results["correct"] / results["total"] if results["total"] > 0 else 0
        
        return results
    
    def compare(self, chatbot1, name1: str, chatbot2, name2: str, limit: int = None) -> Dict:
        """So sánh 2 chatbot."""
        logger.info(f"Evaluating {name1}...")
        results1 = self.evaluate_chatbot(chatbot1, name1, limit)
        
        logger.info(f"Evaluating {name2}...")
        results2 = self.evaluate_chatbot(chatbot2, name2, limit)
        
        return {
            "chatbot1": results1,
            "chatbot2": results2
        }
    
    def print_comparison(self, results: Dict):
        """In kết quả so sánh."""
        r1 = results["chatbot1"]
        r2 = results["chatbot2"]
        
        print()
        print("=" * 70)
        print("📊 KẾT QUẢ SO SÁNH")
        print("=" * 70)
        print()
        
        # Header
        print(f"{'Metric':<30} {r1['name']:>18} {r2['name']:>18}")
        print("-" * 70)
        
        # Overall accuracy
        print(f"{'📈 Tổng accuracy':<30} {r1['accuracy']*100:>17.2f}% {r2['accuracy']*100:>17.2f}%")
        print(f"{'   Correct/Total':<30} {r1['correct']:>8}/{r1['total']:<8} {r2['correct']:>8}/{r2['total']:<8}")
        print()
        
        # By type
        print("--- Theo loại câu hỏi ---")
        for q_type in r1["by_type"]:
            t1 = r1["by_type"][q_type]
            t2 = r2["by_type"].get(q_type, {"correct": 0, "total": 0})
            acc1 = t1["correct"]/t1["total"]*100 if t1["total"] > 0 else 0
            acc2 = t2["correct"]/t2["total"]*100 if t2["total"] > 0 else 0
            print(f"  {q_type:<28} {acc1:>17.2f}% {acc2:>17.2f}%")
        print()
        
        # By hops
        print("--- Theo số hop ---")
        for hops in sorted(r1["by_hops"].keys()):
            h1 = r1["by_hops"][hops]
            h2 = r2["by_hops"].get(hops, {"correct": 0, "total": 0})
            acc1 = h1["correct"]/h1["total"]*100 if h1["total"] > 0 else 0
            acc2 = h2["correct"]/h2["total"]*100 if h2["total"] > 0 else 0
            print(f"  {hops}-hop:<28 {acc1:>17.2f}% {acc2:>17.2f}%")
        print()
        
        # Time
        print(f"{'⏱️ Thời gian':<30} {r1['time']:>17.2f}s {r2['time']:>17.2f}s")
        print()
        
        # Winner
        print("=" * 70)
        if r1["accuracy"] > r2["accuracy"]:
            diff = (r1["accuracy"] - r2["accuracy"]) * 100
            print(f"🏆 {r1['name']} thắng với chênh lệch {diff:.2f}%")
        elif r2["accuracy"] > r1["accuracy"]:
            diff = (r2["accuracy"] - r1["accuracy"]) * 100
            print(f"🏆 {r2['name']} thắng với chênh lệch {diff:.2f}%")
        else:
            print("🤝 Hòa!")
        print("=" * 70)
        
        # Sample errors
        print()
        print(f"--- Lỗi mẫu của {r1['name']} ---")
        for err in r1["errors"][:3]:
            print(f"  Q: {err['question']}...")
            print(f"     Expected: {err['expected']}, Got: {err['got']}")
        
        print()
        print(f"--- Lỗi mẫu của {r2['name']} ---")
        for err in r2["errors"][:3]:
            print(f"  Q: {err['question']}...")
            print(f"     Expected: {err['expected']}, Got: {err['got']}")


def main():
    import os
    
    # Kiểm tra API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Chưa có GEMINI_API_KEY!")
        print()
        print("Để chạy so sánh, bạn cần:")
        print("1. Lấy API key tại: https://makersuite.google.com/app/apikey")
        print("2. Set environment variable:")
        print("   export GEMINI_API_KEY='your-api-key'")
        print()
        print("Hoặc chạy trực tiếp:")
        print("   GEMINI_API_KEY='your-key' python compare_chatbots.py")
        return
    
    # Khởi tạo chatbots
    print("🚀 Khởi tạo GraphRAG Chatbot...")
    from chatbot.llm_chatbot import LLMGraphChatbot
    graph_chatbot = LLMGraphChatbot()
    graph_chatbot.initialize()
    
    print("🚀 Khởi tạo Gemini Chatbot...")
    gemini_chatbot = GeminiChatbot(api_key)
    
    # So sánh
    evaluator = ComparisonEvaluator("data/evaluation/eval_dataset.json")
    
    # Chạy với 100 câu để test nhanh
    print()
    print("📊 Bắt đầu so sánh (100 câu hỏi)...")
    print("⚠️ Gemini có rate limit nên sẽ chậm (~3 phút)")
    print()
    
    results = evaluator.compare(
        graph_chatbot, "GraphRAG (Ours)",
        gemini_chatbot, "Gemini 2.5 Flash",
        limit=100  # Test với 100 câu trước
    )
    
    evaluator.print_comparison(results)
    
    # Lưu kết quả
    with open("reports/comparison_results.json", "w", encoding="utf-8") as f:
        # Convert để có thể serialize
        save_results = {
            "chatbot1": {
                "name": results["chatbot1"]["name"],
                "accuracy": results["chatbot1"]["accuracy"],
                "correct": results["chatbot1"]["correct"],
                "total": results["chatbot1"]["total"],
                "time": results["chatbot1"]["time"]
            },
            "chatbot2": {
                "name": results["chatbot2"]["name"],
                "accuracy": results["chatbot2"]["accuracy"],
                "correct": results["chatbot2"]["correct"],
                "total": results["chatbot2"]["total"],
                "time": results["chatbot2"]["time"]
            }
        }
        json.dump(save_results, f, ensure_ascii=False, indent=2)
    
    print()
    print("💾 Đã lưu kết quả vào reports/comparison_results.json")


if __name__ == "__main__":
    main()
