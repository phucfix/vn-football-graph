#!/usr/bin/env python3
"""
Script to run chatbot comparison evaluation.

Usage:
    # Quick test (100 questions)
    python -m chatbot.run_comparison --quick --gemini-key YOUR_API_KEY
    
    # Full evaluation (all 2500 questions)  
    python -m chatbot.run_comparison --full --gemini-key YOUR_API_KEY
    
    # Custom number of questions
    python -m chatbot.run_comparison --questions 500 --gemini-key YOUR_API_KEY
    
    # Only GraphRAG with LLM (no Gemini)
    python -m chatbot.run_comparison --graphrag-only --use-llm
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Run chatbot comparison evaluation")
    parser.add_argument("--gemini-key", type=str, help="Google API key for Gemini")
    parser.add_argument("--questions", type=int, default=100, help="Number of questions to evaluate")
    parser.add_argument("--quick", action="store_true", help="Quick test with 100 questions")
    parser.add_argument("--full", action="store_true", help="Full evaluation with all questions")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM in GraphRAG chatbot")
    parser.add_argument("--hybrid", action="store_true", help="Use Hybrid chatbot (Graph + LLM formatting)")
    parser.add_argument("--graphrag-only", action="store_true", help="Only evaluate GraphRAG (no Gemini)")
    parser.add_argument("--gemini-only", action="store_true", help="Only evaluate Gemini")
    
    args = parser.parse_args()
    
    # Determine number of questions
    if args.full:
        max_questions = None  # All questions
    elif args.quick:
        max_questions = 100
    else:
        max_questions = args.questions
        
    # Set API key if provided
    if args.gemini_key:
        os.environ["GOOGLE_API_KEY"] = args.gemini_key
    
    from chatbot.evaluator import (
        evaluate_graphrag_chatbot,
        evaluate_gemini_chatbot,
        run_full_comparison,
        EVALUATION_DIR
    )
    
    # Determine mode description
    if args.hybrid:
        mode_desc = "Hybrid (Graph + LLM)"
    elif args.use_llm:
        mode_desc = "Pure LLM"
    else:
        mode_desc = "Rule-based (no LLM)"
    
    print("\n" + "="*70)
    print("🚀 VIETNAM FOOTBALL CHATBOT EVALUATION")
    print("="*70)
    print(f"📊 Questions to evaluate: {max_questions or 'ALL (2500)'}")
    print(f"🤖 GraphRAG mode: {mode_desc}")
    print(f"🔮 Compare with Gemini: {'No' if args.graphrag_only else 'Yes'}")
    print("="*70)
    
    results = {}
    
    # Run GraphRAG evaluation
    if not args.gemini_only:
        print(f"\n📊 Evaluating GraphRAG Chatbot ({mode_desc})...")
        try:
            graphrag_summary = evaluate_graphrag_chatbot(
                max_questions=max_questions, 
                use_llm=args.use_llm,
                hybrid=args.hybrid
            )
            results["GraphRAG"] = graphrag_summary
        except Exception as e:
            print(f"❌ GraphRAG evaluation failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Run Gemini evaluation
    if not args.graphrag_only:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("\n⚠️ GOOGLE_API_KEY/GEMINI_API_KEY not set. Skipping Gemini evaluation.")
            print("   Use --gemini-key YOUR_KEY to enable Gemini comparison.")
        else:
            print(f"\n📊 Evaluating Gemini...")
            try:
                gemini_summary = evaluate_gemini_chatbot(max_questions=max_questions)
                results["Gemini"] = gemini_summary
            except Exception as e:
                print(f"❌ Gemini evaluation failed: {e}")
                import traceback
                traceback.print_exc()
    
    # Print final comparison
    if len(results) >= 1:
        print("\n" + "="*80)
        print("📊 FINAL RESULTS")
        print("="*80)
        
        print(f"\n{'Model':<25} {'Accuracy':<12} {'T/F':<10} {'Y/N':<10} {'MCQ':<10}")
        print("-"*70)
        for name, summary in results.items():
            print(f"{summary.model_name:<25} {summary.accuracy:>10.2%} "
                  f"{summary.accuracy_true_false:>8.2%} "
                  f"{summary.accuracy_yes_no:>8.2%} "
                  f"{summary.accuracy_mcq:>8.2%}")
        
        print(f"\n{'Model':<25} {'1-hop':<12} {'2-hop':<10} {'3-hop':<10} {'Avg Time':<10}")
        print("-"*70)
        for name, summary in results.items():
            print(f"{summary.model_name:<25} {summary.accuracy_1hop:>10.2%} "
                  f"{summary.accuracy_2hop:>8.2%} "
                  f"{summary.accuracy_3hop:>8.2%} "
                  f"{summary.avg_response_time:>8.3f}s")
        
        print("="*80)
        
        # Winner analysis
        if len(results) >= 2:
            graphrag = results.get("GraphRAG")
            gemini = results.get("Gemini")
            if graphrag and gemini:
                print("\n📈 ANALYSIS:")
                if graphrag.accuracy > gemini.accuracy:
                    diff = (graphrag.accuracy - gemini.accuracy) * 100
                    print(f"   ✅ GraphRAG is {diff:.1f}% more accurate than Gemini")
                elif gemini.accuracy > graphrag.accuracy:
                    diff = (gemini.accuracy - graphrag.accuracy) * 100
                    print(f"   ⚠️ Gemini is {diff:.1f}% more accurate than GraphRAG")
                else:
                    print(f"   🤝 Both models have the same accuracy")
                    
                # Multi-hop comparison
                print(f"\n   Multi-hop reasoning comparison:")
                print(f"   - 2-hop: GraphRAG {graphrag.accuracy_2hop:.1%} vs Gemini {gemini.accuracy_2hop:.1%}")
                print(f"   - 3-hop: GraphRAG {graphrag.accuracy_3hop:.1%} vs Gemini {gemini.accuracy_3hop:.1%}")
                
                # Speed comparison
                if graphrag.avg_response_time < gemini.avg_response_time:
                    speedup = gemini.avg_response_time / graphrag.avg_response_time
                    print(f"\n   ⚡ GraphRAG is {speedup:.1f}x faster than Gemini")
                else:
                    speedup = graphrag.avg_response_time / gemini.avg_response_time
                    print(f"\n   ⚡ Gemini is {speedup:.1f}x faster than GraphRAG")
        
        print(f"\n💾 Results saved to {EVALUATION_DIR}")
    
    return results


if __name__ == "__main__":
    main()
