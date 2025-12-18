#!/bin/bash

# Unset the problematic environment variable
unset GITHUB_TOKEN

# Refresh GitHub CLI authentication
echo "Refreshing GitHub CLI authentication..."
gh auth refresh -h github.com -s repo

# Commit if needed
echo "Checking git status..."
if git status | grep -q "nothing to commit"; then
    echo "✓ Already committed"
else
    echo "Committing changes..."
    git commit -m "feat: complete advanced league system implementation with backend services, database schema, and frontend templates"
fi

# Push
echo "Pushing to GitHub..."
git push origin master

echo "✓ Successfully pushed!"
