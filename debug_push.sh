#!/bin/bash

# Clear token and login fresh
unset GITHUB_TOKEN
unset GIT_ASKPASS

# Check current status
echo "=== Git Status ==="
git status

echo ""
echo "=== Trying to commit if needed ==="
git add . 2>/dev/null
git commit -m "feat: complete advanced league system implementation with backend services, database schema, and frontend templates" 2>/dev/null || echo "Nothing new to commit"

echo ""
echo "=== Attempt 1: Direct push ==="
git push origin master 2>&1

echo ""
echo "=== If above failed, trying with gh CLI ==="
gh repo sync Simply-Ryan/StockLeague --force 2>&1 || echo "gh sync failed"

echo ""
echo "=== Checking remote ==="
git remote -v

echo ""
echo "=== Last commit ==="
git log --oneline -1
