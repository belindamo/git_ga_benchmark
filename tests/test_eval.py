#!/usr/bin/env python3
"""
Test script for the git-qa-benchmark evaluation system.

This script tests the evaluation system with mock answers of varying quality
to ensure the scoring works correctly.
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path to import eval module
sys.path.append(str(Path(__file__).parent.parent))

from eval import evaluate_task, load_tasks


def test_evaluation_with_mock_answers():
    """Test the evaluation system with mock answers of different quality levels."""
    
    # Load the tasks
    tasks = load_tasks()
    
    # Find the teleprompter crash task
    teleprompter_task = None
    for task in tasks:
        if task["task_id"] == "pattern_recognition_teleprompter_crash":
            teleprompter_task = task
            break
    
    if not teleprompter_task:
        print("❌ Could not find teleprompter crash task")
        return False
    
    # Define mock answer files and expected score ranges
    test_cases = [
        {
            "file": "tests/mock/pattern_recognition_teleprompter_crash_excellent.txt",
            "expected_min": 0.75,  # Should score 75%+
            "expected_max": 1.0,
            "description": "Excellent answer"
        },
        {
            "file": "tests/mock/pattern_recognition_teleprompter_crash_good.txt", 
            "expected_min": 0.60,  # Should score 60-79%
            "expected_max": 0.79,
            "description": "Good answer"
        },
        {
            "file": "tests/mock/pattern_recognition_teleprompter_crash_fair.txt",
            "expected_min": 0.40,  # Should score 40-65%
            "expected_max": 0.65,
            "description": "Fair answer"
        },
        {
            "file": "tests/mock/pattern_recognition_teleprompter_crash_poor.txt",
            "expected_min": 0.0,   # Should score 0-24%
            "expected_max": 0.24,
            "description": "Poor answer"
        }
    ]
    
    results = []
    all_passed = True
    
    print("🧪 Testing evaluation system with mock answers...")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['description']}")
        
        # Check if mock file exists
        if not Path(test_case["file"]).exists():
            print(f"❌ Mock file not found: {test_case['file']}")
            all_passed = False
            continue
        
        try:
            # Run evaluation
            result = evaluate_task(
                teleprompter_task,
                agent_answer_path=test_case["file"]
            )
            
            score = result.score
            expected_min = test_case["expected_min"]
            expected_max = test_case["expected_max"]
            
            # Check if score is in expected range
            if expected_min <= score <= expected_max:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
                all_passed = False
            
            print(f"  Score: {score:.2f} (expected: {expected_min:.2f}-{expected_max:.2f}) {status}")
            
            # Show breakdown
            details = result.details
            print(f"    Pattern Recognition: {details['pattern_recognition']}/25")
            print(f"    Specific Evidence: {details['specific_evidence']}/25") 
            print(f"    Root Cause Analysis: {details['root_cause_analysis']}/25")
            print(f"    Actionable Insights: {details['actionable_insights']}/25")
            print(f"    Total: {details['total_score']}/100")
            print()
            
            results.append({
                "test_case": test_case["description"],
                "score": score,
                "expected_range": f"{expected_min:.2f}-{expected_max:.2f}",
                "passed": expected_min <= score <= expected_max,
                "details": details
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            all_passed = False
            results.append({
                "test_case": test_case["description"],
                "error": str(e),
                "passed": False
            })
            print()
    
    # Save detailed results
    results_file = Path("tests/eval_test_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "summary": {
                "all_tests_passed": all_passed,
                "total_tests": len(test_cases),
                "passed_tests": sum(1 for r in results if r.get("passed", False))
            },
            "results": results
        }, f, indent=2)
    
    print(f"📄 Detailed results saved to: {results_file}")
    
    # Final summary
    passed_count = sum(1 for r in results if r.get("passed", False))
    print(f"\n📊 Summary: {passed_count}/{len(test_cases)} tests passed")
    
    if all_passed:
        print("🎉 All tests passed! Evaluation system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the results above.")
    
    return all_passed


def test_basic_functionality():
    """Test basic functionality of the evaluation system."""
    print("🔧 Testing basic evaluation functionality...")
    
    try:
        # Test loading tasks
        tasks = load_tasks()
        print(f"✅ Successfully loaded {len(tasks)} tasks")
        
        # Test that all required files exist
        for task in tasks:
            task_id = task["task_id"]
            source_file = Path(f"dataset_from_dspy/source_answers/{task_id}.md")
            if not source_file.exists():
                print(f"❌ Missing source answer: {source_file}")
                return False
            else:
                print(f"✅ Found source answer: {task_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting git-qa-benchmark evaluation tests")
    print("=" * 50)
    print()
    
    # Test basic functionality first
    basic_test_passed = test_basic_functionality()
    print()
    
    if not basic_test_passed:
        print("❌ Basic functionality tests failed. Stopping.")
        sys.exit(1)
    
    # Test with mock answers
    mock_test_passed = test_evaluation_with_mock_answers()
    
    print()
    print("=" * 50)
    
    if basic_test_passed and mock_test_passed:
        print("🎉 All tests passed! Evaluation system is ready to use.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main() 