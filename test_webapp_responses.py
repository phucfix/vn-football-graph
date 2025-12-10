#!/usr/bin/env python3
"""
Test Suite for Vietnam Football Chatbot - Flask Web App Version
Tests chatbot.chat() method (returns full sentences like in web interface)
"""

import json
import logging
from typing import List, Dict
from datetime import datetime
from chatbot.chatbot import HybridChatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCase:
    """Represents a single test case."""
    def __init__(self, question: str, expected_keywords: List[str] = None, 
                 should_contain: str = None, should_not_contain: str = None,
                 category: str = None, difficulty: str = "medium"):
        self.question = question
        self.expected_keywords = expected_keywords or []  # Keywords that should appear
        self.should_contain = should_contain  # Must contain this string
        self.should_not_contain = should_not_contain  # Must NOT contain this
        self.category = category
        self.difficulty = difficulty
        
        # Results
        self.actual_answer = None
        self.passed = None
        self.error = None
        self.notes = ""


def generate_test_cases() -> List[TestCase]:
    """Generate comprehensive test cases."""
    test_cases = []
    
    # ========== TRUE STATEMENTS (Should affirm) ==========
    test_cases.extend([
        TestCase(
            "Công Phượng có chơi cho HAGL không?",
            expected_keywords=["có", "đúng", "phải", "hagl", "công phượng"],
            should_not_contain="không",
            category="played_for_positive",
            difficulty="easy"
        ),
        TestCase(
            "Quang Hải từng khoác áo Hà Nội FC",
            expected_keywords=["có", "đúng", "phải", "hà nội", "quang hải"],
            should_not_contain="không",
            category="played_for_positive",
            difficulty="easy"
        ),
        TestCase(
            "Công Phượng sinh ở Nghệ An",
            expected_keywords=["có", "đúng", "phải", "nghệ an", "công phượng"],
            should_not_contain="không",
            category="born_in_positive",
            difficulty="easy"
        ),
        TestCase(
            "Park Hang-seo có huấn luyện tuyển Việt Nam không?",
            expected_keywords=["có", "đúng", "park", "tuyển", "việt nam"],
            should_not_contain="không",
            category="coach_positive",
            difficulty="easy"
        ),
        TestCase(
            "Công Phượng và Quang Hải là đồng đội tuyển Việt Nam",
            expected_keywords=["có", "đúng", "đồng đội", "tuyển"],
            should_not_contain="không",
            category="teammates_positive",
            difficulty="medium"
        ),
    ])
    
    # ========== FALSE STATEMENTS (Should deny) ==========
    test_cases.extend([
        TestCase(
            "Công Phượng chơi cho Hà Nội FC",
            expected_keywords=["không", "sai"],
            should_contain="không",
            category="played_for_negative",
            difficulty="easy"
        ),
        TestCase(
            "Quang Hải sinh ở Nghệ An",
            expected_keywords=["không", "sai", "hà nội"],
            should_contain="không",
            category="born_in_negative",
            difficulty="easy"
        ),
        TestCase(
            "Công Phượng và Quang Hải chơi cùng CLB",
            expected_keywords=["không"],
            should_contain="không",
            category="same_club_negative",
            difficulty="medium"
        ),
    ])
    
    # ========== OPEN QUESTIONS (Check answer quality) ==========
    test_cases.extend([
        TestCase(
            "Công Phượng chơi cho CLB nào?",
            expected_keywords=["hagl", "hoàng anh gia lai"],
            category="what_club",
            difficulty="easy"
        ),
        TestCase(
            "Quang Hải sinh năm nào?",
            expected_keywords=["1997"],
            category="birth_year",
            difficulty="medium"
        ),
        TestCase(
            "Công Phượng sinh ở đâu?",
            expected_keywords=["nghệ an"],
            category="birthplace",
            difficulty="easy"
        ),
        TestCase(
            "Sân Mỹ Đình ở đâu?",
            expected_keywords=["hà nội"],
            category="stadium_location",
            difficulty="easy"
        ),
    ])
    
    # ========== COMPLEX QUESTIONS ==========
    test_cases.extend([
        TestCase(
            "Công Phượng và Văn Toàn có từng chơi cùng câu lạc bộ không?",
            expected_keywords=["có", "hagl"],
            category="multi_hop",
            difficulty="medium"
        ),
        TestCase(
            "Quang Hải chơi cho CLB ở Hà Nội không?",
            expected_keywords=["có", "đúng", "hà nội"],
            category="multi_hop",
            difficulty="hard"
        ),
    ])
    
    # ========== NATURAL VARIATIONS ==========
    test_cases.extend([
        TestCase(
            "Cho tôi biết Công Phượng chơi cho đội nào?",
            expected_keywords=["hagl"],
            category="natural_phrasing",
            difficulty="easy"
        ),
        TestCase(
            "Quang Hải là cầu thủ của câu lạc bộ nào?",
            expected_keywords=["hà nội"],
            category="natural_phrasing",
            difficulty="easy"
        ),
        TestCase(
            "Công Phượng có phải cầu thủ Việt Nam không?",
            expected_keywords=["có", "đúng", "phải", "việt nam"],
            category="natural_phrasing",
            difficulty="easy"
        ),
    ])
    
    return test_cases


def evaluate_answer(test_case: TestCase) -> bool:
    """
    Evaluate if answer is correct based on keywords and constraints.
    Returns True if test passes.
    """
    answer_lower = test_case.actual_answer.lower()
    
    # Check must-contain constraint
    if test_case.should_contain:
        if test_case.should_contain.lower() not in answer_lower:
            test_case.notes = f"Missing required: '{test_case.should_contain}'"
            return False
    
    # Check must-not-contain constraint
    if test_case.should_not_contain:
        if test_case.should_not_contain.lower() in answer_lower:
            test_case.notes = f"Contains forbidden: '{test_case.should_not_contain}'"
            return False
    
    # Check if at least one expected keyword is present
    if test_case.expected_keywords:
        found_keywords = [kw for kw in test_case.expected_keywords if kw.lower() in answer_lower]
        if not found_keywords:
            test_case.notes = f"Missing keywords: {test_case.expected_keywords}"
            return False
        else:
            test_case.notes = f"Found: {found_keywords}"
            return True
    
    # If no constraints, consider it passed
    return True


def run_test(chatbot: HybridChatbot, test_case: TestCase) -> TestCase:
    """Run a single test case."""
    try:
        # Call chat() method like Flask app does
        answer = chatbot.chat(test_case.question)
        test_case.actual_answer = answer
        test_case.passed = evaluate_answer(test_case)
                
    except Exception as e:
        test_case.error = str(e)
        test_case.passed = False
        test_case.actual_answer = f"ERROR: {e}"
        logger.error(f"Error: {e}")
    
    return test_case


def main():
    """Main test runner."""
    print("="*80)
    print("VIETNAM FOOTBALL CHATBOT - WEB APP TEST SUITE")
    print("Testing chat() method with full sentence responses")
    print("="*80)
    
    # Initialize chatbot
    print("\n🚀 Initializing HybridChatbot (with LLM)...")
    print("⏳ Loading Qwen2-0.5B model...\n")
    chatbot = HybridChatbot()
    if not chatbot.initialize():
        print("❌ Failed to initialize chatbot!")
        return
    print("\n✅ Chatbot ready! Starting tests...\n")
    
    # Generate tests
    test_cases = generate_test_cases()
    print(f"📝 Running {len(test_cases)} tests...\n")
    
    # Run tests
    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "failed_cases": []
    }
    
    for i, tc in enumerate(test_cases, 1):
        run_test(chatbot, tc)
        
        if tc.passed:
            results["passed"] += 1
            status = "✅"
        else:
            results["failed"] += 1
            results["failed_cases"].append(tc)
            status = "❌"
        
        # Track by category
        cat = tc.category or "other"
        if cat not in results["by_category"]:
            results["by_category"][cat] = {"total": 0, "passed": 0}
        results["by_category"][cat]["total"] += 1
        if tc.passed:
            results["by_category"][cat]["passed"] += 1
        
        # Print progress
        print(f"[{i:2d}/{len(test_cases)}] {status} {tc.question[:55]}")
        print(f"       Answer: {tc.actual_answer[:80]}...")
        if not tc.passed:
            print(f"       Note: {tc.notes}")
        print()
    
    # Print summary
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}\n")
    
    pass_rate = (results["passed"] / results["total"] * 100)
    print(f"📊 Overall: {results['passed']}/{results['total']} ({pass_rate:.1f}%)\n")
    
    print("📂 By Category:")
    for cat, stats in sorted(results["by_category"].items()):
        cat_rate = (stats["passed"] / stats["total"] * 100)
        print(f"   {cat:30} {stats['passed']:2}/{stats['total']:2} ({cat_rate:5.1f}%)")
    
    # Show failed cases
    if results["failed_cases"]:
        print(f"\n{'='*80}")
        print(f"❌ Failed Cases ({len(results['failed_cases'])})")
        print(f"{'='*80}\n")
        for i, tc in enumerate(results["failed_cases"], 1):
            print(f"{i}. Q: {tc.question}")
            print(f"   A: {tc.actual_answer}")
            print(f"   Note: {tc.notes}")
            print(f"   Category: {tc.category}\n")
    
    # Save results
    output_file = "test_results_webapp.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": results["total"],
                "passed": results["passed"],
                "failed": results["failed"],
                "pass_rate": pass_rate
            },
            "by_category": results["by_category"],
            "test_cases": [
                {
                    "question": tc.question,
                    "answer": tc.actual_answer,
                    "passed": tc.passed,
                    "notes": tc.notes,
                    "category": tc.category,
                    "difficulty": tc.difficulty
                }
                for tc in test_cases
            ]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    chatbot.close()
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
