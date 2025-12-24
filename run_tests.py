#!/usr/bin/env python3
"""
run_tests.py

Comprehensive test runner for StockLeague.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py unit         # Run only unit tests
    python run_tests.py integration  # Run only integration tests
    python run_tests.py -v           # Run with verbose output
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def discover_tests(test_type=None):
    """
    Discover and return test suite.
    
    Args:
        test_type: 'unit', 'integration', or None for all
    
    Returns:
        unittest.TestSuite
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    tests_dir = PROJECT_ROOT / 'tests'
    
    if test_type is None or test_type == 'unit':
        unit_tests = loader.discover(
            str(tests_dir / 'unit'),
            pattern='test_*.py'
        )
        suite.addTests(unit_tests)
    
    if test_type is None or test_type == 'integration':
        integration_tests = loader.discover(
            str(tests_dir / 'integration'),
            pattern='test_*.py'
        )
        suite.addTests(integration_tests)
    
    return suite


def run_tests(test_type=None, verbosity=1):
    """
    Run the test suite.
    
    Args:
        test_type: 'unit', 'integration', or None for all
        verbosity: Test output verbosity level (0-2)
    
    Returns:
        TestResult object
    """
    suite = discover_tests(test_type)
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return result


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run StockLeague test suite'
    )
    parser.add_argument(
        'test_type',
        nargs='?',
        choices=['unit', 'integration'],
        help='Type of tests to run (default: all)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=1,
        help='Increase output verbosity'
    )
    parser.add_argument(
        '--pattern',
        default='test_*.py',
        help='Pattern for test file names'
    )
    parser.add_argument(
        '--failfast',
        action='store_true',
        help='Stop on first failure'
    )
    
    args = parser.parse_args()
    
    # Run tests
    suite = discover_tests(args.test_type)
    runner = unittest.TextTestRunner(
        verbosity=args.verbose,
        failfast=args.failfast
    )
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("="*70)
    
    # Exit with appropriate code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
