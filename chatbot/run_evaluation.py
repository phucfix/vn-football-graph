"""
Run Evaluation Script for Vietnam Football Knowledge Graph Chatbot

Usage:
    # Generate questions
    python -m chatbot.run_evaluation --generate --num-questions 2500
    
    # Evaluate GraphRAG chatbot
    python -m chatbot.run_evaluation --evaluate --max-questions 500
    
    # Compare with external chatbots
    python -m chatbot.run_evaluation --compare --external openai
    
    # Full pipeline
    python -m chatbot.run_evaluation --full
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.question_generator import QuestionGenerator, generate_evaluation_dataset
from chatbot.evaluator import (
    ChatbotEvaluator, 
    ComparisonEvaluator, 
    ExternalChatbotEvaluator,
    evaluate_graphrag_chatbot
)
from chatbot.config import EVALUATION_DIR, QUESTIONS_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_questions(num_questions: int = 2500):
    """Generate evaluation questions."""
    logger.info(f"📝 Generating {num_questions} evaluation questions...")
    
    filepath = generate_evaluation_dataset(num_questions)
    
    logger.info(f"✅ Questions saved to: {filepath}")
    return filepath


def evaluate_chatbot(max_questions: int = None):
    """Evaluate the GraphRAG chatbot."""
    logger.info("🔄 Evaluating GraphRAG Chatbot...")
    
    summary = evaluate_graphrag_chatbot(max_questions)
    
    logger.info("✅ Evaluation complete!")
    return summary


def compare_chatbots(external_api: str = None, max_questions: int = 100):
    """Compare GraphRAG chatbot with external chatbots."""
    from chatbot.chatbot import SimpleChatbot
    
    logger.info("📊 Running comparison evaluation...")
    
    # Initialize comparison
    comparison = ComparisonEvaluator()
    
    # Add GraphRAG chatbot
    graphrag_chatbot = SimpleChatbot()
    if graphrag_chatbot.initialize():
        graphrag_evaluator = ChatbotEvaluator(graphrag_chatbot, model_name="GraphRAG")
        comparison.add_evaluator("GraphRAG", graphrag_evaluator)
    
    # Add external chatbot if specified
    if external_api:
        external = ExternalChatbotEvaluator(api_type=external_api)
        
        # Create evaluator with custom answer function
        external_evaluator = ChatbotEvaluator(model_name=f"External-{external_api}")
        external_evaluator.chatbot = external  # Hack to use external answerer
        
        # Override answer function
        def external_answer(question):
            return external.answer_question(question)
            
        comparison.add_evaluator(f"{external_api.upper()}", external_evaluator)
    
    # Run comparison
    results = comparison.run_comparison(
        questions_file=QUESTIONS_FILE,
        max_questions=max_questions
    )
    
    # Print and save
    comparison.print_comparison()
    comparison.save_comparison()
    
    # Cleanup
    graphrag_chatbot.close()
    
    return results


def run_full_pipeline(num_questions: int = 2500, eval_questions: int = 500):
    """Run the full evaluation pipeline."""
    logger.info("🚀 Running full evaluation pipeline...")
    
    # Step 1: Generate questions (if not exist)
    if not QUESTIONS_FILE.exists():
        logger.info("\n📝 Step 1: Generating questions...")
        generate_questions(num_questions)
    else:
        logger.info(f"\n📂 Step 1: Using existing questions from {QUESTIONS_FILE}")
        
    # Step 2: Evaluate GraphRAG chatbot
    logger.info("\n🔄 Step 2: Evaluating GraphRAG chatbot...")
    summary = evaluate_chatbot(eval_questions)
    
    # Step 3: Print results
    logger.info("\n📊 Step 3: Results Summary")
    print("\n" + "="*60)
    print("🎯 FINAL EVALUATION RESULTS")
    print("="*60)
    print(f"\nModel: {summary.model_name}")
    print(f"Questions Evaluated: {summary.total_questions}")
    print(f"\n📈 Overall Accuracy: {summary.accuracy:.2%}")
    print(f"\n📋 By Question Type:")
    print(f"   - True/False: {summary.accuracy_true_false:.2%}")
    print(f"   - Yes/No: {summary.accuracy_yes_no:.2%}")
    print(f"   - MCQ: {summary.accuracy_mcq:.2%}")
    print(f"\n🔗 By Reasoning Depth (Multi-hop):")
    print(f"   - 1-hop (Direct): {summary.accuracy_1hop:.2%}")
    print(f"   - 2-hop: {summary.accuracy_2hop:.2%}")
    print(f"   - 3-hop: {summary.accuracy_3hop:.2%}")
    print(f"\n⏱️ Average Response Time: {summary.avg_response_time:.3f}s")
    print("="*60)
    
    return summary


def interactive_demo():
    """Run interactive demo of the chatbot."""
    from chatbot.chatbot import SimpleChatbot
    
    print("\n" + "="*60)
    print("🤖 VIETNAM FOOTBALL KNOWLEDGE GRAPH CHATBOT")
    print("="*60)
    print("\nĐang khởi tạo chatbot...")
    
    chatbot = SimpleChatbot()
    if not chatbot.initialize():
        print("❌ Không thể khởi tạo chatbot!")
        return
        
    print("✅ Chatbot đã sẵn sàng!")
    print("\nNhập câu hỏi về bóng đá Việt Nam (gõ 'quit' để thoát):")
    print("-"*60)
    
    while True:
        try:
            user_input = input("\n🧑 Bạn: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Tạm biệt!")
                break
                
            if not user_input:
                continue
                
            # Get response
            response = chatbot.chat(user_input)
            print(f"\n🤖 Chatbot: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
            
    chatbot.close()


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Vietnam Football Knowledge Graph Chatbot"
    )
    
    parser.add_argument(
        "--generate", 
        action="store_true",
        help="Generate evaluation questions"
    )
    parser.add_argument(
        "--evaluate", 
        action="store_true",
        help="Evaluate GraphRAG chatbot"
    )
    parser.add_argument(
        "--compare", 
        action="store_true",
        help="Compare with external chatbots"
    )
    parser.add_argument(
        "--full", 
        action="store_true",
        help="Run full evaluation pipeline"
    )
    parser.add_argument(
        "--demo", 
        action="store_true",
        help="Run interactive demo"
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=2500,
        help="Number of questions to generate (default: 2500)"
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=None,
        help="Maximum questions to evaluate (default: all)"
    )
    parser.add_argument(
        "--external",
        type=str,
        choices=["openai", "google"],
        help="External API for comparison (openai or google)"
    )
    
    args = parser.parse_args()
    
    # Default to full pipeline if no action specified
    if not any([args.generate, args.evaluate, args.compare, args.full, args.demo]):
        args.full = True
        
    try:
        if args.generate:
            generate_questions(args.num_questions)
            
        if args.evaluate:
            evaluate_chatbot(args.max_questions)
            
        if args.compare:
            compare_chatbots(args.external, args.max_questions or 100)
            
        if args.full:
            run_full_pipeline(args.num_questions, args.max_questions or 500)
            
        if args.demo:
            interactive_demo()
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
