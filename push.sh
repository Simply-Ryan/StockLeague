#!/bin/bash

# Commit if not already committed
if git status | grep -q "nothing to commit"; then
    echo "✓ Already committed, proceeding to push..."
else
    echo "Committing changes..."
    git commit -m "feat: complete advanced league system implementation with backend services, database schema, and frontend templates"
fi

# Try to get git credentials
echo "Authenticating with GitHub..."
gh auth refresh -h github.com -s repo

# Push
echo "Pushing to GitHub..."
git push origin master

echo "✓ Done!"
