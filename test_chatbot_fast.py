#!/usr/bin/env python3
"""
Test Suite for Vietnam Football Chatbot
Tests HybridChatbot (used in Flask app) - includes LLM formatting
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
    def __init__(self, question: str, question_type: str, expected_answer: str = None, 
                 category: str = None, difficulty: str = "medium"):
        self.question = question
        self.question_type = question_type
        self.expected_answer = expected_answer
        self.category = category
        self.difficulty = difficulty
        self.actual_answer = None
        self.confidence = None
        self.passed = None
        self.error = None


def generate_test_cases() -> List[TestCase]:
    """Generate comprehensive test cases."""
    test_cases = []
    
    # ========== TRUE/FALSE - DIRECT (1-HOP) ==========
    test_cases.extend([
        # PLAYED_FOR
        TestCase("Công Phượng có chơi cho HAGL không?", "yes_no", "Có", "played_for", "easy"),
        TestCase("Công Phượng chơi cho HAGL", "yes_no", "Có", "played_for", "easy"),
        TestCase("Quang Hải có chơi cho Hà Nội không?", "yes_no", "Có", "played_for", "easy"),
        TestCase("Văn Toàn chơi cho HAGL", "yes_no", "Có", "played_for", "easy"),
        TestCase("Tuấn Anh có chơi cho HAGL không?", "yes_no", "Có", "played_for", "easy"),
        TestCase("Công Phượng có chơi cho Viettel không?", "yes_no", "Không", "played_for", "easy"),
        TestCase("Quang Hải từng chơi cho HAGL", "yes_no", "Không", "played_for", "easy"),
        
        # BORN_IN
        TestCase("Công Phượng sinh ra ở Nghệ An không?", "yes_no", "Có", "born_in", "easy"),
        TestCase("Công Phượng sinh ở Nghệ An", "yes_no", "Có", "born_in", "easy"),
        TestCase("Quang Hải quê ở Hà Nội", "yes_no", "Có", "born_in", "easy"),
        TestCase("Văn Toàn sinh ra tại Gia Lai", "yes_no", "Có", "born_in", "easy"),
        TestCase("Công Phượng sinh ra ở Hà Nội", "yes_no", "Không", "born_in", "easy"),
        
        # NATIONAL_TEAM
        TestCase("Công Phượng có chơi cho tuyển Việt Nam không?", "yes_no", "Có", "national_team", "easy"),
        TestCase("Quang Hải từng khoác áo đội tuyển Việt Nam", "yes_no", "Có", "national_team", "easy"),
        TestCase("Văn Toàn là cầu thủ tuyển Việt Nam", "yes_no", "Có", "national_team", "easy"),
        TestCase("Park Hang-seo có huấn luyện tuyển Việt Nam không?", "yes_no", "Có", "national_team", "easy"),
        
        # CLUB_LOCATION
        TestCase("HAGL có trụ sở ở Gia Lai không?", "yes_no", "Có", "club_location", "easy"),
        TestCase("Hà Nội FC đặt trụ sở tại Hà Nội", "yes_no", "Có", "club_location", "easy"),
        TestCase("HAGL có trụ sở ở Hà Nội không?", "yes_no", "Không", "club_location", "easy"),
        
        # STADIUM
        TestCase("Sân Mỹ Đình có ở Hà Nội không?", "yes_no", "Có", "stadium", "easy"),
        TestCase("Sân Thống Nhất nằm ở TP.HCM", "yes_no", "Có", "stadium", "easy"),
    ])
    
    # ========== TRUE/FALSE - MULTI-HOP (2-HOP) ==========
    test_cases.extend([
        # SAME CLUB
        TestCase("Công Phượng và Văn Toàn có từng chơi cùng câu lạc bộ không?", "yes_no", "Có", "same_club", "medium"),
        TestCase("Công Phượng và Văn Toàn cùng CLB", "yes_no", "Có", "same_club", "medium"),
        TestCase("Tuấn Anh và Văn Toàn từng là đồng đội CLB", "yes_no", "Có", "same_club", "medium"),
        TestCase("Quang Hải và Công Phượng có chơi cùng CLB không?", "yes_no", "Không", "same_club", "medium"),
        
        # TEAMMATES
        TestCase("Công Phượng và Quang Hải có phải đồng đội không?", "yes_no", "Có", "teammates", "medium"),
        TestCase("Quang Hải và Văn Toàn là đồng đội tuyển Việt Nam", "yes_no", "Có", "teammates", "medium"),
        
        # SAME PROVINCE
        TestCase("Văn Toàn và Tuấn Anh có cùng quê không?", "yes_no", "Có", "same_province", "medium"),
        TestCase("Văn Toàn và Tuấn Anh cùng quê", "yes_no", "Có", "same_province", "medium"),
    ])
    
    # ========== TRUE/FALSE - COMPLEX (3-HOP) ==========
    test_cases.extend([
        TestCase("Công Phượng chơi cho CLB ở Gia Lai không?", "yes_no", "Có", "player_club_province", "hard"),
        TestCase("Quang Hải có chơi cho CLB ở Hà Nội không?", "yes_no", "Có", "player_club_province", "hard"),
    ])
    
    # ========== MULTIPLE CHOICE ==========
    test_cases.extend([
        # Player's Club
        TestCase("Văn Toàn chơi cho CLB nào? | Hà Nội | HAGL | Viettel", "mcq", "HAGL", "mcq_club", "easy"),
        TestCase("Công Phượng chơi cho câu lạc bộ nào? | HAGL | Hà Nội | Viettel", "mcq", "HAGL", "mcq_club", "easy"),
        TestCase("Quang Hải thi đấu cho đội nào? | Hà Nội | HAGL | Viettel", "mcq", "Hà Nội", "mcq_club", "easy"),
        
        # Player's Birthplace
        TestCase("Công Phượng sinh ở đâu? | Nghệ An | Hà Nội | Gia Lai", "mcq", "Nghệ An", "mcq_birthplace", "easy"),
        TestCase("Quang Hải quê ở tỉnh nào? | Hà Nội | Nghệ An | Gia Lai", "mcq", "Hà Nội", "mcq_birthplace", "easy"),
        TestCase("Văn Toàn sinh ra ở đâu? | Gia Lai | Hà Nội | Nghệ An", "mcq", "Gia Lai", "mcq_birthplace", "easy"),
        
        # Birth Year
        TestCase("Công Phượng sinh năm nào? | 1995 | 1997 | 1999", "mcq", "1995", "mcq_birth_year", "medium"),
        TestCase("Quang Hải sinh năm bao nhiêu? | 1995 | 1997 | 1999", "mcq", "1997", "mcq_birth_year", "medium"),
        
        # Position
        TestCase("Quang Hải đá vị trí gì? | Tiền đạo | Tiền vệ | Hậu vệ", "mcq", "Tiền vệ", "mcq_position", "easy"),
        TestCase("Công Phượng chơi ở vị trí nào? | Tiền đạo | Tiền vệ | Hậu vệ", "mcq", "Tiền đạo", "mcq_position", "easy"),
        
        # Stadium
        TestCase("Sân Thống Nhất nằm ở đâu? | TP.HCM | Hà Nội | Đà Nẵng", "mcq", "TP.HCM", "mcq_stadium", "easy"),
        TestCase("Sân Mỹ Đình ở tỉnh nào? | Hà Nội | TP.HCM | Nghệ An", "mcq", "Hà Nội", "mcq_stadium", "easy"),
        
        # Club Location
        TestCase("HAGL có trụ sở ở đâu? | Gia Lai | Hà Nội | Đà Nẵng", "mcq", "Gia Lai", "mcq_club_location", "easy"),
    ])
    
    # ========== EDGE CASES ==========
    test_cases.extend([
        # No question mark
        TestCase("Công Phượng chơi cho HAGL", "yes_no", "Có", "no_question_mark", "easy"),
        TestCase("Quang Hải là cầu thủ Hà Nội", "yes_no", "Có", "no_question_mark", "easy"),
        
        # Different phrasing
        TestCase("Công Phượng có phải cầu thủ của HAGL không?", "yes_no", "Có", "different_phrasing", "easy"),
        TestCase("HAGL có Công Phượng trong đội hình không?", "yes_no", "Có", "different_phrasing", "medium"),
        
        # Reverse order
        TestCase("HAGL có Công Phượng chơi không?", "yes_no", "Có", "reverse_order", "medium"),
        TestCase("Nghệ An là quê của Công Phượng", "yes_no", "Có", "reverse_order", "medium"),
    ])
    
    # ========== NEGATIVE CASES ==========
    test_cases.extend([
        TestCase("Công Phượng chơi cho Hà Nội FC", "yes_no", "Không", "negative", "easy"),
        TestCase("Quang Hải sinh ở Nghệ An", "yes_no", "Không", "negative", "easy"),
        TestCase("Văn Toàn chơi cho Viettel", "yes_no", "Không", "negative", "easy"),
    ])
    
    # ========== GENERAL KNOWLEDGE ==========
    test_cases.extend([
        TestCase("Văn Toàn là cầu thủ Việt Nam?", "yes_no", "Có", "general", "easy"),
        TestCase("Công Phượng là cầu thủ bóng đá", "yes_no", "Có", "general", "easy"),
    ])
    
    return test_cases


def run_test(chatbot: HybridChatbot, test_case: TestCase) -> TestCase:
    """Run a single test case."""
    try:
        if test_case.question_type == "yes_no":
            # HybridChatbot returns (answer, confidence, explanation)
            answer, confidence, explanation = chatbot.answer_yes_no(test_case.question)
            test_case.actual_answer = answer
            test_case.confidence = confidence
            
            if test_case.expected_answer:
                expected_lower = test_case.expected_answer.lower()
                actual_lower = answer.lower()
                
                if expected_lower in ["có", "đúng", "yes", "true"]:
                    test_case.passed = actual_lower in ["có", "đúng", "yes", "true"]
                elif expected_lower in ["không", "sai", "no", "false"]:
                    test_case.passed = actual_lower in ["không", "sai", "no", "false"]
                else:
                    test_case.passed = expected_lower in actual_lower
                    
        elif test_case.question_type == "mcq":
            parts = test_case.question.split("|")
            question = parts[0].strip()
            choices = [c.strip() for c in parts[1:]]
            
            # HybridChatbot returns (answer, confidence, explanation)
            answer, confidence, explanation = chatbot.answer_mcq(question, choices)
            test_case.actual_answer = answer
            test_case.confidence = confidence
            
            if test_case.expected_answer:
                expected_lower = test_case.expected_answer.lower()
                actual_lower = answer.lower()
                test_case.passed = expected_lower in actual_lower or actual_lower in expected_lower
                
    except Exception as e:
        test_case.error = str(e)
        test_case.passed = False
        test_case.confidence = 0.0
        logger.error(f"Error: {e}")
    
    return test_case


def main():
    """Main test runner."""
    print("="*80)
    print("VIETNAM FOOTBALL CHATBOT - HYBRID TEST SUITE (Flask App)")
    print("="*80)
    
    # Initialize chatbot
    print("\n🚀 Initializing HybridChatbot (with LLM)...")
    print("⏳ This will take a moment to load Qwen2-0.5B model...\n")
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
        
        if i % 10 == 0 or not tc.passed:
            conf_str = f"{tc.confidence:.2f}" if tc.confidence is not None else "N/A"
            print(f"[{i:3d}/{len(test_cases)}] {status} {tc.question[:50]}... "
                  f"(exp: {tc.expected_answer}, got: {tc.actual_answer}, conf: {conf_str})")
    
    # Print summary
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}\n")
    
    pass_rate = (results["passed"] / results["total"] * 100)
    print(f"📊 Overall: {results['passed']}/{results['total']} ({pass_rate:.1f}%)\n")
    
    print("📂 By Category:")
    for cat, stats in sorted(results["by_category"].items()):
        cat_rate = (stats["passed"] / stats["total"] * 100)
        print(f"   {cat:25} {stats['passed']:3}/{stats['total']:3} ({cat_rate:5.1f}%)")
    
    # Failed cases
    if results["failed_cases"]:
        print(f"\n❌ Failed Cases ({len(results['failed_cases'])}):\n")
        for i, tc in enumerate(results["failed_cases"][:30], 1):
            print(f"{i:2d}. Q: {tc.question}")
            print(f"    Expected: {tc.expected_answer}, Got: {tc.actual_answer} (conf: {tc.confidence:.2f})")
            print(f"    Category: {tc.category}\n")
    
    # Save results
    output_file = "test_results_hybrid.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": results["total"],
                "passed": results["passed"],
                "failed": results["failed"],
                "pass_rate": (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
            },
            "by_category": results["by_category"],
            "failed_cases": [
                {
                    "question": tc.question,
                    "expected": tc.expected_answer,
                    "actual": tc.actual_answer,
                    "confidence": tc.confidence,
                    "category": tc.category,
                    "difficulty": tc.difficulty
                }
                for tc in results["failed_cases"]
            ]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    chatbot.close()
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
