"""
Run all tests across all 3 backends and generate combined coverage report
"""
import subprocess
import sys
import os

def run_tests():
    """Run tests for all backends and combine coverage"""
    print("=" * 80)
    print("Running All Backend Tests - Combined Coverage Report")
    print("=" * 80)
    
    # Set up coverage for all backends
    os.environ['COVERAGE_FILE'] = '.coverage'
    
    # Run all tests from unified tests/ directory
    print("\nAll Backend Tests (Unified)...")
    subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=app",
        "--cov=tests",
        "--cov=AslBackend/app",
        "--cov=color-cue/app",
        "-v"
    ])
    
    # Generate combined HTML report
    print("\nGenerating combined coverage report...")
    subprocess.run([
        sys.executable, "-m", "coverage",
        "html",
        "-d", "htmlcov_combined"
    ])
    
    # Generate terminal report
    print("\n" + "=" * 80)
    print("COMBINED COVERAGE REPORT - ALL BACKENDS")
    print("=" * 80 + "\n")
    subprocess.run([
        sys.executable, "-m", "coverage",
        "report",
        "--skip-empty"
    ])
    
    print("\n" + "=" * 80)
    print("Combined coverage report generated!")
    print(f"Open: htmlcov_combined\\index.html")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()

