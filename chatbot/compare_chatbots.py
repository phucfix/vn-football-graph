#!/usr/bin/env python3
"""
Script so sánh GraphRAG Chatbot với External Chatbots (ChatGPT/Gemini)

Sử dụng:
    python compare_chatbots.py --sample-size 100

Yêu cầu:
    - OPENAI_API_KEY trong .env (cho ChatGPT)
    - GOOGLE_API_KEY trong .env (cho Gemini)
"""

import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import random

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths
QUESTIONS_FILE = Path("chatbot/evaluation/questions.json")
RESULTS_FILE = Path("chatbot/evaluation/results.json")
COMPARISON_FILE = Path("chatbot/evaluation/comparison_results.json")


@dataclass
class ComparisonResult:
    """Kết quả so sánh giữa các chatbots"""
    question_id: str
    question_text: str
    question_type: str
    correct_answer: str
    graphrag_answer: str
    graphrag_correct: bool
    graphrag_confidence: float
    chatgpt_answer: Optional[str] = None
    chatgpt_correct: Optional[bool] = None
    gemini_answer: Optional[str] = None
    gemini_correct: Optional[bool] = None


class ExternalChatbotClient:
    """Client cho external chatbots"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        self._openai_client = None
        self._gemini_model = None
        
    def _init_openai(self):
        """Initialize OpenAI client"""
        if self._openai_client is None and self.openai_api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info("✅ OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed. Run: pip install openai")
            except Exception as e:
                logger.error(f"Failed to init OpenAI: {e}")
                
    def _init_gemini(self):
        """Initialize Google Gemini"""
        if self._gemini_model is None and self.google_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_api_key)
                self._gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("✅ Gemini model initialized")
            except ImportError:
                logger.warning("Google AI package not installed. Run: pip install google-generativeai")
            except Exception as e:
                logger.error(f"Failed to init Gemini: {e}")
    
    def ask_chatgpt(self, question: str, choices: List[str] = None) -> Tuple[str, float]:
        """Ask ChatGPT a question"""
        self._init_openai()
        
        if not self._openai_client:
            return "", 0.0
            
        try:
            # Format prompt
            if choices:
                choices_text = "\n".join([f"- {c}" for c in choices])
                prompt = f"""Trả lời câu hỏi về bóng đá Việt Nam. Chỉ trả lời bằng một trong các lựa chọn được cho.

Câu hỏi: {question}

Các lựa chọn:
{choices_text}

Chỉ trả lời bằng một lựa chọn, không giải thích."""
            else:
                prompt = f"""Trả lời câu hỏi về bóng đá Việt Nam. 
Nếu là câu hỏi Đúng/Sai, chỉ trả lời "Đúng" hoặc "Sai".
Nếu là câu hỏi Có/Không, chỉ trả lời "Có" hoặc "Không".

Câu hỏi: {question}

Trả lời ngắn gọn, không giải thích."""
            
            response = self._openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            answer = response.choices[0].message.content.strip()
            return answer, 0.8  # Confidence estimate
            
        except Exception as e:
            logger.error(f"ChatGPT error: {e}")
            return "", 0.0
            
    def ask_gemini(self, question: str, choices: List[str] = None) -> Tuple[str, float]:
        """Ask Google Gemini a question"""
        self._init_gemini()
        
        if not self._gemini_model:
            return "", 0.0
            
        try:
            # Format prompt
            if choices:
                choices_text = "\n".join([f"- {c}" for c in choices])
                prompt = f"""Trả lời câu hỏi về bóng đá Việt Nam. Chỉ trả lời bằng một trong các lựa chọn được cho.

Câu hỏi: {question}

Các lựa chọn:
{choices_text}

Chỉ trả lời bằng một lựa chọn, không giải thích."""
            else:
                prompt = f"""Trả lời câu hỏi về bóng đá Việt Nam. 
Nếu là câu hỏi Đúng/Sai, chỉ trả lời "Đúng" hoặc "Sai".
Nếu là câu hỏi Có/Không, chỉ trả lời "Có" hoặc "Không".

Câu hỏi: {question}

Trả lời ngắn gọn, không giải thích."""
            
            response = self._gemini_model.generate_content(prompt)
            answer = response.text.strip()
            return answer, 0.8  # Confidence estimate
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "", 0.0


def normalize_answer(answer: str, correct_answer: str) -> str:
    """Normalize answer for comparison"""
    answer = answer.strip().lower()
    correct_lower = correct_answer.lower()
    
    # True/False normalization
    if correct_lower in ["đúng", "sai"]:
        if any(x in answer for x in ["đúng", "true", "yes", "correct"]):
            return "đúng"
        if any(x in answer for x in ["sai", "false", "no", "incorrect"]):
            return "sai"
            
    # Yes/No normalization  
    if correct_lower in ["có", "không"]:
        if any(x in answer for x in ["có", "yes", "đúng"]):
            return "có"
        if any(x in answer for x in ["không", "no", "sai"]):
            return "không"
    
    # MCQ - find matching choice
    return answer


def check_answer(predicted: str, correct: str) -> bool:
    """Check if answer is correct"""
    pred_norm = normalize_answer(predicted, correct)
    correct_norm = correct.lower().strip()
    
    return pred_norm == correct_norm or correct_norm in pred_norm or pred_norm in correct_norm


def load_graphrag_results() -> Dict:
    """Load GraphRAG evaluation results"""
    if not RESULTS_FILE.exists():
        logger.error(f"Results file not found: {RESULTS_FILE}")
        return {}
        
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_questions() -> List[Dict]:
    """Load evaluation questions"""
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['questions']


def run_comparison(sample_size: int = 100, 
                   use_chatgpt: bool = True,
                   use_gemini: bool = True) -> Dict:
    """
    Run comparison between GraphRAG and external chatbots.
    
    Args:
        sample_size: Number of questions to sample
        use_chatgpt: Whether to evaluate with ChatGPT
        use_gemini: Whether to evaluate with Gemini
        
    Returns:
        Comparison summary
    """
    # Load data
    graphrag_results = load_graphrag_results()
    questions = load_questions()
    
    if not graphrag_results or not questions:
        logger.error("Failed to load data")
        return {}
        
    # Create lookup for GraphRAG results
    graphrag_lookup = {}
    for r in graphrag_results.get('results', []):
        graphrag_lookup[r['question_id']] = r
    
    # Sample questions
    sample_questions = random.sample(questions, min(sample_size, len(questions)))
    logger.info(f"📊 Comparing on {len(sample_questions)} questions")
    
    # Initialize external client
    client = ExternalChatbotClient()
    
    # Run comparison
    results = []
    
    for q in tqdm(sample_questions, desc="Comparing"):
        question_id = q['question_id']
        graphrag_result = graphrag_lookup.get(question_id, {})
        
        result = ComparisonResult(
            question_id=question_id,
            question_text=q['question_text'],
            question_type=q['question_type'],
            correct_answer=q['correct_answer'],
            graphrag_answer=graphrag_result.get('predicted_answer', ''),
            graphrag_correct=graphrag_result.get('is_correct', False),
            graphrag_confidence=graphrag_result.get('confidence', 0.0)
        )
        
        choices = q.get('choices')
        
        # ChatGPT
        if use_chatgpt and client.openai_api_key:
            try:
                answer, _ = client.ask_chatgpt(q['question_text'], choices)
                result.chatgpt_answer = answer
                result.chatgpt_correct = check_answer(answer, q['correct_answer'])
            except Exception as e:
                logger.warning(f"ChatGPT error for {question_id}: {e}")
                
        # Gemini
        if use_gemini and client.google_api_key:
            try:
                answer, _ = client.ask_gemini(q['question_text'], choices)
                result.gemini_answer = answer
                result.gemini_correct = check_answer(answer, q['correct_answer'])
            except Exception as e:
                logger.warning(f"Gemini error for {question_id}: {e}")
                
        results.append(result)
    
    # Calculate summary
    summary = calculate_summary(results)
    
    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'sample_size': len(results),
        'summary': summary,
        'results': [asdict(r) for r in results]
    }
    
    with open(COMPARISON_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Results saved to {COMPARISON_FILE}")
    
    return summary


def calculate_summary(results: List[ComparisonResult]) -> Dict:
    """Calculate comparison summary statistics"""
    total = len(results)
    
    graphrag_correct = sum(1 for r in results if r.graphrag_correct)
    chatgpt_correct = sum(1 for r in results if r.chatgpt_correct)
    gemini_correct = sum(1 for r in results if r.gemini_correct)
    
    chatgpt_evaluated = sum(1 for r in results if r.chatgpt_answer)
    gemini_evaluated = sum(1 for r in results if r.gemini_answer)
    
    summary = {
        'total_questions': total,
        'graphrag': {
            'correct': graphrag_correct,
            'accuracy': graphrag_correct / total if total > 0 else 0,
        },
        'chatgpt': {
            'evaluated': chatgpt_evaluated,
            'correct': chatgpt_correct,
            'accuracy': chatgpt_correct / chatgpt_evaluated if chatgpt_evaluated > 0 else 0,
        },
        'gemini': {
            'evaluated': gemini_evaluated,
            'correct': gemini_correct,
            'accuracy': gemini_correct / gemini_evaluated if gemini_evaluated > 0 else 0,
        }
    }
    
    # By question type
    for qtype in ['true_false', 'yes_no', 'mcq']:
        type_results = [r for r in results if r.question_type == qtype]
        if type_results:
            summary[f'{qtype}_graphrag'] = sum(1 for r in type_results if r.graphrag_correct) / len(type_results)
            chatgpt_type = [r for r in type_results if r.chatgpt_answer]
            if chatgpt_type:
                summary[f'{qtype}_chatgpt'] = sum(1 for r in chatgpt_type if r.chatgpt_correct) / len(chatgpt_type)
            gemini_type = [r for r in type_results if r.gemini_answer]
            if gemini_type:
                summary[f'{qtype}_gemini'] = sum(1 for r in gemini_type if r.gemini_correct) / len(gemini_type)
    
    return summary


def print_summary(summary: Dict):
    """Print comparison summary"""
    print("\n" + "=" * 70)
    print("📊 SO SÁNH HIỆU SUẤT CÁC CHATBOT")
    print("=" * 70)
    
    print(f"\n📋 Tổng số câu hỏi: {summary['total_questions']}")
    
    print("\n🎯 Độ chính xác tổng thể:")
    print(f"   GraphRAG:  {summary['graphrag']['accuracy']:.2%} ({summary['graphrag']['correct']}/{summary['total_questions']})")
    
    if summary['chatgpt']['evaluated'] > 0:
        print(f"   ChatGPT:   {summary['chatgpt']['accuracy']:.2%} ({summary['chatgpt']['correct']}/{summary['chatgpt']['evaluated']})")
        
    if summary['gemini']['evaluated'] > 0:
        print(f"   Gemini:    {summary['gemini']['accuracy']:.2%} ({summary['gemini']['correct']}/{summary['gemini']['evaluated']})")
    
    print("\n📋 Theo loại câu hỏi:")
    for qtype in ['true_false', 'yes_no', 'mcq']:
        qtype_name = {'true_false': 'True/False', 'yes_no': 'Yes/No', 'mcq': 'MCQ'}[qtype]
        line = f"   {qtype_name:12}"
        
        if f'{qtype}_graphrag' in summary:
            line += f" GraphRAG: {summary[f'{qtype}_graphrag']:.2%}"
        if f'{qtype}_chatgpt' in summary:
            line += f" | ChatGPT: {summary[f'{qtype}_chatgpt']:.2%}"
        if f'{qtype}_gemini' in summary:
            line += f" | Gemini: {summary[f'{qtype}_gemini']:.2%}"
            
        print(line)
    
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="So sánh GraphRAG với External Chatbots")
    parser.add_argument("--sample-size", type=int, default=100, 
                        help="Số câu hỏi để đánh giá (default: 100)")
    parser.add_argument("--no-chatgpt", action="store_true", 
                        help="Không sử dụng ChatGPT")
    parser.add_argument("--no-gemini", action="store_true", 
                        help="Không sử dụng Gemini")
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting chatbot comparison...")
    
    summary = run_comparison(
        sample_size=args.sample_size,
        use_chatgpt=not args.no_chatgpt,
        use_gemini=not args.no_gemini
    )
    
    if summary:
        print_summary(summary)


if __name__ == "__main__":
    main()
