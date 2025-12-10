#!/usr/bin/env python3
"""
Comprehensive Test Suite for Vietnam Football Chatbot
Tests HybridChatbot with various question types and patterns
"""

import json
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from chatbot.chatbot import HybridChatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCase:
    """Represents a single test case."""
    def __init__(self, question: str, question_type: str, expected_answer: str = None, 
                 category: str = None, difficulty: str = "medium"):
        self.question = question
        self.question_type = question_type  # "yes_no", "mcq", "open"
        self.expected_answer = expected_answer
        self.category = category
        self.difficulty = difficulty
        
        # Results
        self.actual_answer = None
        self.confidence = None
        self.passed = None
        self.error = None
        

def generate_test_cases() -> List[TestCase]:
    """Generate comprehensive test cases covering all patterns."""
    
    test_cases = []
    
    # ========== 1. TRUE/FALSE - DIRECT RELATIONSHIPS (1-HOP) ==========
    
    # 1.1 PLAYED_FOR (Cầu thủ chơi cho CLB)
    test_cases.extend([
        TestCase("Công Phượng có chơi cho HAGL không?", "yes_no", "Có", "played_for", "easy"),
        TestCase("Công Phượng chơi cho HAGL", "yes_no", "Có", "played_for", "easy"),
        TestCase("Quang Hải có chơi cho Hà Nội không?", "yes_no", "Có", "played_for", "easy"),
        TestCase("Quang Hải từng khoác áo Hà Nội FC", "yes_no", "Có", "played_for", "easy"),
        TestCase("Văn Toàn chơi cho HAGL", "yes_no", "Có", "played_for", "easy"),
        TestCase("Tuấn Anh có chơi cho HAGL không?", "yes_no", "Có", "played_for", "easy"),
        TestCase("Công Phượng có chơi cho Viettel không?", "yes_no", "Không", "played_for", "easy"),
        TestCase("Quang Hải từng chơi cho HAGL", "yes_no", "Không", "played_for", "easy"),
        TestCase("Văn Toàn chơi cho Hà Nội FC", "yes_no", "Không", "played_for", "easy"),
    ])
    
    # 1.2 BORN_IN (Nơi sinh)
    test_cases.extend([
        TestCase("Công Phượng sinh ra ở Nghệ An không?", "yes_no", "Có", "born_in", "easy"),
        TestCase("Công Phượng sinh ở Nghệ An", "yes_no", "Có", "born_in", "easy"),
        TestCase("Quang Hải quê ở Hà Nội", "yes_no", "Có", "born_in", "easy"),
        TestCase("Văn Toàn sinh ra tại Gia Lai", "yes_no", "Có", "born_in", "easy"),
        TestCase("Tuấn Anh có quê ở Gia Lai không?", "yes_no", "Có", "born_in", "easy"),
        TestCase("Công Phượng sinh ra ở Hà Nội", "yes_no", "Không", "born_in", "easy"),
        TestCase("Quang Hải quê ở Nghệ An", "yes_no", "Không", "born_in", "easy"),
    ])
    
    # 1.3 NATIONAL_TEAM (Đội tuyển quốc gia)
    test_cases.extend([
        TestCase("Công Phượng có chơi cho tuyển Việt Nam không?", "yes_no", "Có", "national_team", "easy"),
        TestCase("Quang Hải từng khoác áo đội tuyển Việt Nam", "yes_no", "Có", "national_team", "easy"),
        TestCase("Văn Toàn là cầu thủ tuyển Việt Nam", "yes_no", "Có", "national_team", "easy"),
        TestCase("Park Hang-seo có huấn luyện tuyển Việt Nam không?", "yes_no", "Có", "national_team", "easy"),
        TestCase("Park Hang-seo từng dẫn dắt đội tuyển Việt Nam", "yes_no", "Có", "national_team", "easy"),
    ])
    
    # 1.4 CLUB LOCATION (CLB và địa điểm)
    test_cases.extend([
        TestCase("HAGL có trụ sở ở Gia Lai không?", "yes_no", "Có", "club_location", "easy"),
        TestCase("Hà Nội FC đặt trụ sở tại Hà Nội", "yes_no", "Có", "club_location", "easy"),
        TestCase("HAGL có trụ sở ở Hà Nội không?", "yes_no", "Không", "club_location", "easy"),
    ])
    
    # 1.5 STADIUM (Sân vận động)
    test_cases.extend([
        TestCase("Sân Mỹ Đình có ở Hà Nội không?", "yes_no", "Có", "stadium", "easy"),
        TestCase("Sân Thống Nhất nằm ở TP.HCM", "yes_no", "Có", "stadium", "easy"),
        TestCase("Sân Hàng Đẫy ở Hà Nội", "yes_no", "Có", "stadium", "easy"),
    ])
    
    # ========== 2. TRUE/FALSE - MULTI-HOP (2-HOP) ==========
    
    # 2.1 SAME CLUB (Cùng CLB) - 2 hop via PLAYED_FOR
    test_cases.extend([
        TestCase("Công Phượng và Văn Toàn có từng chơi cùng câu lạc bộ không?", "yes_no", "Có", "same_club", "medium"),
        TestCase("Công Phượng và Văn Toàn cùng CLB", "yes_no", "Có", "same_club", "medium"),
        TestCase("Tuấn Anh và Văn Toàn từng là đồng đội CLB", "yes_no", "Có", "same_club", "medium"),
        TestCase("Quang Hải và Công Phượng có chơi cùng CLB không?", "yes_no", "Không", "same_club", "medium"),
    ])
    
    # 2.2 TEAMMATES (Đồng đội) - National team or club
    test_cases.extend([
        TestCase("Công Phượng và Quang Hải có phải đồng đội không?", "yes_no", "Có", "teammates", "medium"),
        TestCase("Quang Hải và Văn Toàn là đồng đội tuyển Việt Nam", "yes_no", "Có", "teammates", "medium"),
        TestCase("Công Phượng và Quang Hải từng là đồng đội ở tuyển Việt Nam", "yes_no", "Có", "teammates", "medium"),
    ])
    
    # 2.3 SAME PROVINCE (Cùng quê) - 2 hop via province
    test_cases.extend([
        TestCase("Văn Toàn và Tuấn Anh có cùng quê không?", "yes_no", "Có", "same_province", "medium"),
        TestCase("Văn Toàn và Tuấn Anh cùng quê", "yes_no", "Có", "same_province", "medium"),
        TestCase("Công Phượng và Tuấn Anh cùng tỉnh", "yes_no", "Không", "same_province", "medium"),
    ])
    
    # ========== 3. TRUE/FALSE - COMPLEX MULTI-HOP (3-HOP) ==========
    
    # 3.1 Player -> Club -> Province
    test_cases.extend([
        TestCase("Công Phượng chơi cho CLB nào ở Gia Lai?", "yes_no", "Có", "player_club_province", "hard"),
        TestCase("Quang Hải có chơi cho CLB ở Hà Nội không?", "yes_no", "Có", "player_club_province", "hard"),
    ])
    
    # 3.2 Club -> Stadium -> Province
    test_cases.extend([
        TestCase("Hà Nội FC có sân nhà ở Hà Nội không?", "yes_no", "Có", "club_stadium_province", "hard"),
    ])
    
    # ========== 4. MULTIPLE CHOICE QUESTIONS ==========
    
    # 4.1 Player's Club
    test_cases.extend([
        TestCase("Văn Toàn chơi cho CLB nào? | Hà Nội | HAGL | Viettel", "mcq", "HAGL", "mcq_club", "easy"),
        TestCase("Công Phượng chơi cho câu lạc bộ nào? | HAGL | Hà Nội | Viettel", "mcq", "HAGL", "mcq_club", "easy"),
        TestCase("Quang Hải thi đấu cho đội nào? | Hà Nội | HAGL | Viettel", "mcq", "Hà Nội", "mcq_club", "easy"),
        TestCase("Tuấn Anh chơi cho CLB nào? | HAGL | Hà Nội | Viettel", "mcq", "HAGL", "mcq_club", "easy"),
    ])
    
    # 4.2 Player's Birthplace
    test_cases.extend([
        TestCase("Công Phượng sinh ở đâu? | Nghệ An | Hà Nội | Gia Lai", "mcq", "Nghệ An", "mcq_birthplace", "easy"),
        TestCase("Quang Hải quê ở tỉnh nào? | Hà Nội | Nghệ An | Gia Lai", "mcq", "Hà Nội", "mcq_birthplace", "easy"),
        TestCase("Văn Toàn sinh ra ở đâu? | Gia Lai | Hà Nội | Nghệ An", "mcq", "Gia Lai", "mcq_birthplace", "easy"),
    ])
    
    # 4.3 Player's Birth Year
    test_cases.extend([
        TestCase("Công Phượng sinh năm nào? | 1995 | 1997 | 1999", "mcq", "1995", "mcq_birth_year", "medium"),
        TestCase("Quang Hải sinh năm bao nhiêu? | 1995 | 1997 | 1999", "mcq", "1997", "mcq_birth_year", "medium"),
    ])
    
    # 4.4 Player's Position
    test_cases.extend([
        TestCase("Quang Hải đá vị trí gì? | Tiền đạo | Tiền vệ | Hậu vệ", "mcq", "Tiền vệ", "mcq_position", "easy"),
        TestCase("Công Phượng chơi ở vị trí nào? | Tiền đạo | Tiền vệ | Hậu vệ", "mcq", "Tiền đạo", "mcq_position", "easy"),
    ])
    
    # 4.5 Stadium Location
    test_cases.extend([
        TestCase("Sân Thống Nhất nằm ở đâu? | TP.HCM | Hà Nội | Đà Nẵng", "mcq", "TP.HCM", "mcq_stadium", "easy"),
        TestCase("Sân Mỹ Đình ở tỉnh nào? | Hà Nội | TP.HCM | Nghệ An", "mcq", "Hà Nội", "mcq_stadium", "easy"),
        TestCase("Sân Hàng Đẫy thuộc thành phố nào? | Hà Nội | TP.HCM | Đà Nẵng", "mcq", "Hà Nội", "mcq_stadium", "easy"),
    ])
    
    # 4.6 Club Location
    test_cases.extend([
        TestCase("HAGL có trụ sở ở đâu? | Gia Lai | Hà Nội | Đà Nẵng", "mcq", "Gia Lai", "mcq_club_location", "easy"),
        TestCase("Hà Nội FC đặt trụ sở tại đâu? | Hà Nội | TP.HCM | Đà Nẵng", "mcq", "Hà Nội", "mcq_club_location", "easy"),
    ])
    
    # ========== 5. EDGE CASES & VARIATIONS ==========
    
    # 5.1 No question mark
    test_cases.extend([
        TestCase("Công Phượng chơi cho HAGL", "yes_no", "Có", "no_question_mark", "easy"),
        TestCase("Quang Hải là cầu thủ Hà Nội", "yes_no", "Có", "no_question_mark", "easy"),
    ])
    
    # 5.2 Different phrasing
    test_cases.extend([
        TestCase("Công Phượng có phải cầu thủ của HAGL không?", "yes_no", "Có", "different_phrasing", "easy"),
        TestCase("Công Phượng có thi đấu cho HAGL không?", "yes_no", "Có", "different_phrasing", "easy"),
        TestCase("HAGL có Công Phượng trong đội hình không?", "yes_no", "Có", "different_phrasing", "medium"),
    ])
    
    # 5.3 Reverse entity order
    test_cases.extend([
        TestCase("HAGL có Công Phượng chơi không?", "yes_no", "Có", "reverse_order", "medium"),
        TestCase("Nghệ An là quê của Công Phượng", "yes_no", "Có", "reverse_order", "medium"),
    ])
    
    # 5.4 Multiple entities same type
    test_cases.extend([
        TestCase("Công Phượng, Văn Toàn và Tuấn Anh có cùng CLB không?", "yes_no", "Có", "multiple_entities", "hard"),
    ])
    
    # ========== 6. NEGATIVE CASES (Should return "Không") ==========
    
    test_cases.extend([
        TestCase("Công Phượng chơi cho Hà Nội FC", "yes_no", "Không", "negative", "easy"),
        TestCase("Quang Hải sinh ở Nghệ An", "yes_no", "Không", "negative", "easy"),
        TestCase("Văn Toàn chơi cho Viettel", "yes_no", "Không", "negative", "easy"),
        TestCase("HAGL có trụ sở ở Hà Nội", "yes_no", "Không", "negative", "easy"),
    ])
    
    # ========== 7. GENERAL KNOWLEDGE ==========
    
    test_cases.extend([
        TestCase("Văn Toàn là cầu thủ Việt Nam?", "yes_no", "Có", "general", "easy"),
        TestCase("Công Phượng là cầu thủ bóng đá", "yes_no", "Có", "general", "easy"),
        TestCase("Park Hang-seo là huấn luyện viên", "yes_no", "Có", "general", "easy"),
    ])
    
    # ========== 8. COMPLEX MCQ ==========
    
    test_cases.extend([
        TestCase("Cầu thủ nào chơi cho HAGL? | Quang Hải | Công Phượng | Văn Quyết", "mcq", "Công Phượng", "mcq_complex", "medium"),
        TestCase("Ai là huấn luyện viên tuyển Việt Nam? | Park Hang-seo | Troussier | Calisto", "mcq", "Park Hang-seo", "mcq_complex", "medium"),
    ])
    
    return test_cases


def run_test(chatbot: HybridChatbot, test_case: TestCase) -> TestCase:
    """Run a single test case."""
    try:
        if test_case.question_type == "yes_no":
            # True/False question
            answer, confidence, explanation = chatbot.answer_yes_no(test_case.question)
            test_case.actual_answer = answer
            test_case.confidence = confidence
            
            # Check if answer matches expected
            if test_case.expected_answer:
                expected_lower = test_case.expected_answer.lower()
                actual_lower = answer.lower()
                
                # Normalize answers
                if expected_lower in ["có", "đúng", "yes", "true"]:
                    test_case.passed = actual_lower in ["có", "đúng", "yes", "true"]
                elif expected_lower in ["không", "sai", "no", "false"]:
                    test_case.passed = actual_lower in ["không", "sai", "no", "false"]
                else:
                    test_case.passed = expected_lower in actual_lower or actual_lower in expected_lower
            
        elif test_case.question_type == "mcq":
            # Multiple choice question
            parts = test_case.question.split("|")
            question = parts[0].strip()
            choices = [c.strip() for c in parts[1:]]
            
            answer, confidence, explanation = chatbot.answer_mcq(question, choices)
            test_case.actual_answer = answer
            test_case.confidence = confidence
            
            # Check if answer matches expected
            if test_case.expected_answer:
                expected_lower = test_case.expected_answer.lower()
                actual_lower = answer.lower()
                test_case.passed = expected_lower in actual_lower or actual_lower in expected_lower
                
    except Exception as e:
        test_case.error = str(e)
        test_case.passed = False
        logger.error(f"Error testing '{test_case.question}': {e}")
    
    return test_case


def run_all_tests(chatbot: HybridChatbot, test_cases: List[TestCase]) -> Dict:
    """Run all test cases and collect results."""
    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "by_category": {},
        "by_difficulty": {},
        "failed_cases": [],
        "low_confidence_cases": []
    }
    
    print(f"\n{'='*80}")
    print(f"Running {len(test_cases)} test cases...")
    print(f"{'='*80}\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] Testing: {test_case.question[:60]}...", end=" ")
        
        run_test(chatbot, test_case)
        
        # Update results
        if test_case.error:
            results["errors"] += 1
            print("❌ ERROR")
        elif test_case.passed:
            results["passed"] += 1
            print(f"✅ PASS (conf: {test_case.confidence:.2f})")
        else:
            results["failed"] += 1
            print(f"❌ FAIL (expected: {test_case.expected_answer}, got: {test_case.actual_answer})")
            results["failed_cases"].append(test_case)
        
        # Track by category
        if test_case.category:
            if test_case.category not in results["by_category"]:
                results["by_category"][test_case.category] = {"total": 0, "passed": 0, "failed": 0}
            results["by_category"][test_case.category]["total"] += 1
            if test_case.passed:
                results["by_category"][test_case.category]["passed"] += 1
            else:
                results["by_category"][test_case.category]["failed"] += 1
        
        # Track by difficulty
        if test_case.difficulty not in results["by_difficulty"]:
            results["by_difficulty"][test_case.difficulty] = {"total": 0, "passed": 0, "failed": 0}
        results["by_difficulty"][test_case.difficulty]["total"] += 1
        if test_case.passed:
            results["by_difficulty"][test_case.difficulty]["passed"] += 1
        else:
            results["by_difficulty"][test_case.difficulty]["failed"] += 1
        
        # Track low confidence
        if test_case.confidence and test_case.confidence < 0.7:
            results["low_confidence_cases"].append(test_case)
    
    return results


def print_results(results: Dict):
    """Print test results summary."""
    print(f"\n{'='*80}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*80}\n")
    
    # Overall results
    total = results["total"]
    passed = results["passed"]
    failed = results["failed"]
    errors = results["errors"]
    
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"📊 Overall Results:")
    print(f"   Total:   {total}")
    print(f"   Passed:  {passed} ({pass_rate:.1f}%)")
    print(f"   Failed:  {failed}")
    print(f"   Errors:  {errors}")
    
    # By category
    print(f"\n📂 Results by Category:")
    for category, stats in sorted(results["by_category"].items()):
        cat_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"   {category:25} {stats['passed']:3}/{stats['total']:3} ({cat_pass_rate:5.1f}%)")
    
    # By difficulty
    print(f"\n⚡ Results by Difficulty:")
    for difficulty in ["easy", "medium", "hard"]:
        if difficulty in results["by_difficulty"]:
            stats = results["by_difficulty"][difficulty]
            diff_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"   {difficulty:10} {stats['passed']:3}/{stats['total']:3} ({diff_pass_rate:5.1f}%)")
    
    # Failed cases
    if results["failed_cases"]:
        print(f"\n❌ Failed Cases ({len(results['failed_cases'])}):")
        for i, test_case in enumerate(results["failed_cases"][:20], 1):  # Show first 20
            print(f"\n   {i}. Question: {test_case.question}")
            print(f"      Expected: {test_case.expected_answer}")
            print(f"      Got:      {test_case.actual_answer}")
            print(f"      Category: {test_case.category}")
            if test_case.confidence:
                print(f"      Confidence: {test_case.confidence:.2f}")
    
    # Low confidence cases
    if results["low_confidence_cases"]:
        print(f"\n⚠️  Low Confidence Cases ({len(results['low_confidence_cases'])}):")
        for i, test_case in enumerate(results["low_confidence_cases"][:10], 1):  # Show first 10
            print(f"\n   {i}. Question: {test_case.question}")
            print(f"      Answer:     {test_case.actual_answer}")
            print(f"      Confidence: {test_case.confidence:.2f}")


def save_results(results: Dict, test_cases: List[TestCase], filename: str = "test_results.json"):
    """Save test results to JSON file."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": results["total"],
            "passed": results["passed"],
            "failed": results["failed"],
            "errors": results["errors"],
            "pass_rate": (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
        },
        "by_category": results["by_category"],
        "by_difficulty": results["by_difficulty"],
        "failed_cases": [
            {
                "question": tc.question,
                "question_type": tc.question_type,
                "expected": tc.expected_answer,
                "actual": tc.actual_answer,
                "confidence": tc.confidence,
                "category": tc.category,
                "difficulty": tc.difficulty,
                "error": tc.error
            }
            for tc in results["failed_cases"]
        ],
        "low_confidence_cases": [
            {
                "question": tc.question,
                "answer": tc.actual_answer,
                "confidence": tc.confidence,
                "category": tc.category
            }
            for tc in results["low_confidence_cases"]
        ]
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")


def main():
    """Main test runner."""
    print("="*80)
    print("VIETNAM FOOTBALL CHATBOT - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    # Initialize chatbot
    print("\n🚀 Initializing chatbot...")
    chatbot = HybridChatbot()
    if not chatbot.initialize():
        print("❌ Failed to initialize chatbot!")
        return
    print("✅ Chatbot initialized!\n")
    
    # Generate test cases
    print("📝 Generating test cases...")
    test_cases = generate_test_cases()
    print(f"✅ Generated {len(test_cases)} test cases\n")
    
    # Run tests
    results = run_all_tests(chatbot, test_cases)
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, test_cases)
    
    # Cleanup
    chatbot.close()
    
    print(f"\n{'='*80}")
    print("Testing completed!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
