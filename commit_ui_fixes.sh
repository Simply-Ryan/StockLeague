#!/bin/bash

unset GITHUB_TOKEN

# Navigate to repo
cd /workspaces/codespaces-blank/StockLeague

# Add changes
git add -A

# Commit
git commit -m "fix: improve navbar contrast and home page UI for non-registered users

- Fix navbar text color contrast (white text on dark background)
- Update guest navbar buttons with better styling
- Improve home hero section with better spacing and typography
- Enhance feature cards with improved hover effects and borders
- Update stats section with gradient background
- Improve CTA section styling and layout
- Increase font weights and sizes for better hierarchy"

echo "✓ Commit complete"
