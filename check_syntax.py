#!/usr/bin/env python3
"""Check syntax of test file"""
import ast
import sys

try:
    with open('/workspaces/StockLeague/tests/test_engagement_features.py', 'r') as f:
        code = f.read()
    
    ast.parse(code)
    print("✓ Syntax is valid!")
    sys.exit(0)
except SyntaxError as e:
    print(f"✗ Syntax error: {e}")
    print(f"  Line {e.lineno}: {e.text}")
    sys.exit(1)
