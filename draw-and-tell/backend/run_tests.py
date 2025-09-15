#!/usr/bin/env python3
"""
Test Runner for Draw and Tell Backend
Runs all unit tests and provides comprehensive test reporting
"""

import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

def run_tests():
    """Run all unit tests and generate report"""
    print("🧪 Draw and Tell - Unit Test Suite")
    print("=" * 50)
    print(f"Test run started at: {datetime.now().isoformat()}")
    print()
    
    # Get the backend directory
    backend_dir = Path(__file__).parent
    test_dir = backend_dir / "tests"
    
    # Test files to run
    test_files = [
        "test_safety_service.py",
        "test_cv_service.py", 
        "test_tts_service.py",
        "test_asr_service.py",
        "test_prompt_service.py",
        "test_local_storage.py",
        "test_kid_loop_router.py"
    ]
    
    # Results storage
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "test_files": [],
        "overall_status": "PASSED"
    }
    
    # Run each test file
    for test_file in test_files:
        test_path = test_dir / test_file
        if not test_path.exists():
            print(f"⚠️  Test file not found: {test_file}")
            continue
            
        print(f"🔍 Running {test_file}...")
        
        try:
            # Run pytest on the specific test file
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_path), 
                "-v", 
                "--tb=short",
                "--json-report",
                "--json-report-file=test_results.json"
            ], capture_output=True, text=True, cwd=backend_dir)
            
            # Parse results
            file_result = {
                "file": test_file,
                "status": "PASSED" if result.returncode == 0 else "FAILED",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            # Try to parse JSON report if it exists
            json_report_path = backend_dir / "test_results.json"
            if json_report_path.exists():
                try:
                    with open(json_report_path, 'r') as f:
                        json_data = json.load(f)
                        file_result["summary"] = json_data.get("summary", {})
                        file_result["total_tests"] = json_data.get("summary", {}).get("total", 0)
                        file_result["passed"] = json_data.get("summary", {}).get("passed", 0)
                        file_result["failed"] = json_data.get("summary", {}).get("failed", 0)
                except:
                    pass
                finally:
                    # Clean up JSON report
                    if json_report_path.exists():
                        json_report_path.unlink()
            
            results["test_files"].append(file_result)
            
            if result.returncode == 0:
                print(f"✅ {test_file}: PASSED")
                results["passed_tests"] += 1
            else:
                print(f"❌ {test_file}: FAILED")
                print(f"   Error: {result.stderr}")
                results["failed_tests"] += 1
                results["overall_status"] = "FAILED"
            
            results["total_tests"] += 1
            
        except Exception as e:
            print(f"❌ {test_file}: ERROR - {str(e)}")
            results["test_files"].append({
                "file": test_file,
                "status": "ERROR",
                "error": str(e)
            })
            results["failed_tests"] += 1
            results["overall_status"] = "FAILED"
        
        print()
    
    # Calculate pass rate
    if results["total_tests"] > 0:
        results["pass_rate"] = results["passed_tests"] / results["total_tests"]
    else:
        results["pass_rate"] = 0.0
    
    # Display summary
    print("📊 Test Summary")
    print("-" * 30)
    print(f"Total Test Files: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Pass Rate: {results['pass_rate']:.1%}")
    print(f"Overall Status: {results['overall_status']}")
    print()
    
    # Display detailed results
    print("📋 Detailed Results")
    print("-" * 30)
    for file_result in results["test_files"]:
        status_icon = "✅" if file_result["status"] == "PASSED" else "❌"
        print(f"{status_icon} {file_result['file']}: {file_result['status']}")
        
        if "total_tests" in file_result:
            print(f"   Tests: {file_result.get('passed', 0)}/{file_result.get('total_tests', 0)} passed")
        
        if file_result["status"] == "FAILED" and "stderr" in file_result:
            print(f"   Error: {file_result['stderr'][:100]}...")
    
    # Save detailed results to file
    output_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Return exit code based on results
    return 0 if results["overall_status"] == "PASSED" else 1

def run_specific_test(test_name):
    """Run a specific test file"""
    backend_dir = Path(__file__).parent
    test_path = backend_dir / "tests" / f"test_{test_name}.py"
    
    if not test_path.exists():
        print(f"❌ Test file not found: test_{test_name}.py")
        return 1
    
    print(f"🔍 Running test_{test_name}.py...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_path), 
            "-v", 
            "--tb=short"
        ], cwd=backend_dir)
        
        return result.returncode
    except Exception as e:
        print(f"❌ Error running test: {str(e)}")
        return 1

def list_available_tests():
    """List all available test files"""
    backend_dir = Path(__file__).parent
    test_dir = backend_dir / "tests"
    
    print("📋 Available Test Files:")
    print("-" * 30)
    
    test_files = [
        "safety_service",
        "cv_service", 
        "tts_service",
        "asr_service",
        "prompt_service",
        "local_storage",
        "kid_loop_router"
    ]
    
    for test_name in test_files:
        test_path = test_dir / f"test_{test_name}.py"
        status = "✅" if test_path.exists() else "❌"
        print(f"{status} test_{test_name}.py")

if __name__ == "__main__":
    exit_code = 0
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            list_available_tests()
        elif command == "run":
            if len(sys.argv) > 2:
                test_name = sys.argv[2]
                exit_code = run_specific_test(test_name)
            else:
                exit_code = run_tests()
        else:
            print("Usage: python run_tests.py [list|run [test_name]]")
            exit_code = 1
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)
