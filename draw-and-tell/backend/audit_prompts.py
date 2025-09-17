#!/usr/bin/env python3
"""
Prompt Audit Script for Draw and Tell
Runs comprehensive safety tests to ensure COPPA compliance and jailbreak protection
"""

import sys
import os
import json
from datetime import datetime
from services.safety_service import safety_service

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))



def run_prompt_audit():
    """Run comprehensive prompt audit tests"""
    print("🛡️ Draw and Tell - Prompt Safety Audit")
    print("=" * 50)
    print(f"Audit started at: {datetime.now().isoformat()}")
    print()
    
    # Run the audit
    results = safety_service.audit_prompts()
    
    # Display results
    print(f"📊 Audit Results:")
    print(f"   Total Tests: {results['total_tests']}")
    print(f"   Passed: {results['passed_tests']}")
    print(f"   Failed: {results['failed_tests']}")
    print(f"   Pass Rate: {results['pass_rate']:.1%}")
    print(f"   Overall Status: {results['overall_status']}")
    print()
    
    # Display individual test results
    print("📋 Individual Test Results:")
    print("-" * 50)
    
    for test in results['test_results']:
        status = "✅ PASS" if test['passed'] else "❌ FAIL"
        print(f"{status} {test['test_name']}")
        print(f"   Input: {test['input']}")
        print(f"   Expected: {test['expected_behavior']}")
        print(f"   Actual: {test['actual_behavior']}")
        if test['violations']:
            print(f"   Violations: {', '.join(test['violations'])}")
        print()
    
    # Save results to file
    output_file = f"audit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Detailed results saved to: {output_file}")
    
    # Return exit code based on results
    return 0 if results['overall_status'] == 'PASSED' else 1

if __name__ == "__main__":
    exit_code = run_prompt_audit()
    sys.exit(exit_code)
