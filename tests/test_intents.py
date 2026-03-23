"""
Intent Classification Accuracy Test Suite

Tests the LLM's ability to correctly classify user intents.
Measures accuracy, precision, recall, and identifies problem areas.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.main import ChatRequest, chat, sessions


class IntentEvaluator:
    """Evaluate intent classification accuracy."""
    
    def __init__(self, test_cases_file: str):
        """Load test cases from JSON file."""
        with open(test_cases_file, 'r') as f:
            data = json.load(f)
        self.test_cases = data['test_cases']
        self.results = []
        self.stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    def run_test(self, test_case: Dict) -> Dict:
        """Run a single test case."""
        message = test_case['message']
        expected_intent = test_case['expected_intent']
        category = test_case['category']
        
        # Clear session for fresh test
        sessions.clear()
        
        try:
            # Send message to chatbot
            req = ChatRequest(phone="+260970000000", message=message)
            response = chat(req)
            
            predicted_intent = response['intent']
            confidence = response['confidence']
            
            # Check if correct
            is_correct = predicted_intent == expected_intent
            
            result = {
                'id': test_case['id'],
                'message': message,
                'expected': expected_intent,
                'predicted': predicted_intent,
                'confidence': confidence,
                'correct': is_correct,
                'category': category
            }
            
            # Update stats
            self.stats[category]['total'] += 1
            if is_correct:
                self.stats[category]['correct'] += 1
            
            return result
            
        except Exception as e:
            return {
                'id': test_case['id'],
                'message': message,
                'expected': expected_intent,
                'predicted': 'ERROR',
                'confidence': 0.0,
                'correct': False,
                'category': category,
                'error': str(e)
            }
    
    def run_all_tests(self) -> List[Dict]:
        """Run all test cases."""
        print("🧪 Running Intent Classification Tests...\n")
        
        for i, test_case in enumerate(self.test_cases, 1):
            result = self.run_test(test_case)
            self.results.append(result)
            
            # Print progress
            status = "✅" if result['correct'] else "❌"
            print(f"{status} Test {i}/{len(self.test_cases)}: {result['message'][:40]}...")
            print(f"   Expected: {result['expected']}")
            print(f"   Predicted: {result['predicted']} (confidence: {result['confidence']:.2f})")
            if not result['correct']:
                print(f"   ⚠️ MISMATCH")
            print()
        
        return self.results
    
    def print_summary(self):
        """Print test summary and statistics."""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70 + "\n")
        
        # Overall accuracy
        total_tests = len(self.results)
        correct_tests = sum(1 for r in self.results if r['correct'])
        accuracy = (correct_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Overall Accuracy: {correct_tests}/{total_tests} ({accuracy:.1f}%)\n")
        
        # By category
        print("Accuracy by Category:")
        print("-" * 70)
        for category in sorted(self.stats.keys()):
            stats = self.stats[category]
            cat_accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {category:20s}: {stats['correct']:2d}/{stats['total']:2d} ({cat_accuracy:5.1f}%)")
        
        print("\n" + "-" * 70)
        
        # Failed tests
        failed = [r for r in self.results if not r['correct']]
        if failed:
            print(f"\n❌ Failed Tests ({len(failed)}):")
            print("-" * 70)
            for result in failed:
                print(f"  Test {result['id']}: {result['message'][:50]}")
                print(f"    Expected: {result['expected']}")
                print(f"    Got: {result['predicted']} (confidence: {result['confidence']:.2f})")
                if 'error' in result:
                    print(f"    Error: {result['error']}")
                print()
        
        # Confidence analysis
        print("\n📈 Confidence Analysis:")
        print("-" * 70)
        correct_confidences = [r['confidence'] for r in self.results if r['correct']]
        incorrect_confidences = [r['confidence'] for r in self.results if not r['correct']]
        
        if correct_confidences:
            avg_correct = sum(correct_confidences) / len(correct_confidences)
            print(f"  Avg confidence (correct): {avg_correct:.3f}")
        
        if incorrect_confidences:
            avg_incorrect = sum(incorrect_confidences) / len(incorrect_confidences)
            print(f"  Avg confidence (incorrect): {avg_incorrect:.3f}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        print("-" * 70)
        if accuracy >= 80:
            print("  ✅ Intent classification is reliable (≥80% accuracy)")
        elif accuracy >= 60:
            print("  ⚠️  Intent classification needs improvement (60-80% accuracy)")
            print("     - Review failed test cases")
            print("     - Consider improving LLM prompt")
            print("     - Check for ambiguous intents")
        else:
            print("  ❌ Intent classification is unreliable (<60% accuracy)")
            print("     - Major issues detected")
            print("     - Review LLM configuration")
            print("     - Consider fallback mechanisms")
        
        print("\n" + "="*70 + "\n")
        
        return accuracy
    
    def save_results(self, output_file: str):
        """Save detailed results to JSON file."""
        output = {
            'summary': {
                'total_tests': len(self.results),
                'correct': sum(1 for r in self.results if r['correct']),
                'accuracy': sum(1 for r in self.results if r['correct']) / len(self.results) * 100
            },
            'by_category': dict(self.stats),
            'results': self.results
        }
        
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"📁 Results saved to: {output_file}")


def main():
    """Run the intent evaluation test suite."""
    test_file = Path(__file__).parent / "intent_cases.json"
    
    if not test_file.exists():
        print(f"❌ Test cases file not found: {test_file}")
        sys.exit(1)
    
    # Run tests
    evaluator = IntentEvaluator(str(test_file))
    evaluator.run_all_tests()
    accuracy = evaluator.print_summary()
    
    # Save results
    output_file = Path(__file__).parent / "intent_results.json"
    evaluator.save_results(str(output_file))
    
    # Exit with appropriate code
    sys.exit(0 if accuracy >= 80 else 1)


if __name__ == "__main__":
    main()
