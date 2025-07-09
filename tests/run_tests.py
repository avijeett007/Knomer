#!/usr/bin/env python3
"""
Test runner script for video processing API
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False

def check_test_environment():
    """Check if test environment is properly set up"""
    print("🔍 Checking test environment...")
    
    # Check if test videos exist
    test_videos_dir = Path(__file__).parent / "sample_videos"
    required_files = [
        "Yetti_Patel_s_London_Vlog.mp4",
        "Yetti_Patel_s_UK_Tour_Intro.mp4", 
        "open_door_transition_first_clip.mp4",
        "knolabslogo.png"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = test_videos_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"⚠️  Missing test files: {missing_files}")
        print("Some tests may be skipped")
    else:
        print("✅ All test files found")
    
    # Check if required services are running
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
    except Exception:
        print("⚠️  Redis not available - some tests may fail")
    
    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg is available")
    except Exception:
        print("⚠️  FFmpeg not available - video processing tests will fail")
    
    # Check if Whisper dependencies are available
    try:
        import whisper
        print("✅ Whisper is available")
    except ImportError:
        print("⚠️  Whisper not available - transcription tests will be skipped")

def run_unit_tests():
    """Run unit tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_credit_system.py',
        'tests/test_api_endpoints.py',
        '-v',
        '--tb=short',
        '--durations=10'
    ]
    return run_command(cmd, "Unit Tests")

def run_integration_tests():
    """Run integration tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_video_features.py',
        '-v',
        '--tb=short',
        '--durations=10'
    ]
    return run_command(cmd, "Integration Tests")

def run_e2e_tests():
    """Run end-to-end tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_e2e_video_processing.py',
        '-v',
        '--tb=short',
        '--durations=20',
        '--timeout=600'  # 10 minute timeout for E2E tests
    ]
    return run_command(cmd, "End-to-End Tests")

def run_performance_tests():
    """Run performance tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_performance.py',
        '-v',
        '-m', 'performance',
        '--tb=short',
        '--durations=10'
    ]
    return run_command(cmd, "Performance Tests")

def run_load_tests():
    """Run load tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_performance.py',
        '-v',
        '-m', 'load',
        '--tb=short',
        '--durations=10'
    ]
    return run_command(cmd, "Load Tests")

def run_all_tests():
    """Run all tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--durations=20',
        '--timeout=600'
    ]
    return run_command(cmd, "All Tests")

def generate_coverage_report():
    """Generate test coverage report"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '--cov=services',
        '--cov=api',
        '--cov=models',
        '--cov-report=html',
        '--cov-report=term-missing',
        '--tb=short'
    ]
    return run_command(cmd, "Coverage Report")

def main():
    parser = argparse.ArgumentParser(description='Run video processing API tests')
    parser.add_argument('--type', choices=[
        'unit', 'integration', 'e2e', 'performance', 'load', 'all', 'coverage'
    ], default='all', help='Type of tests to run')
    parser.add_argument('--check-env', action='store_true', 
                       help='Check test environment setup')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    if args.check_env:
        check_test_environment()
        return
    
    print("🚀 Starting Video Processing API Tests")
    print(f"Test type: {args.type}")
    
    # Always check environment first
    check_test_environment()
    
    success = True
    
    if args.type == 'unit':
        success = run_unit_tests()
    elif args.type == 'integration':
        success = run_integration_tests()
    elif args.type == 'e2e':
        success = run_e2e_tests()
    elif args.type == 'performance':
        success = run_performance_tests()
    elif args.type == 'load':
        success = run_load_tests()
    elif args.type == 'coverage':
        success = generate_coverage_report()
    elif args.type == 'all':
        # Run tests in order of complexity
        tests = [
            ('Unit Tests', run_unit_tests),
            ('Integration Tests', run_integration_tests),
            ('End-to-End Tests', run_e2e_tests),
            ('Performance Tests', run_performance_tests)
        ]
        
        results = {}
        for test_name, test_func in tests:
            results[test_name] = test_func()
            if not results[test_name]:
                print(f"⚠️  {test_name} failed, continuing with other tests...")
        
        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
        
        success = all(results.values())
    
    if success:
        print(f"\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
