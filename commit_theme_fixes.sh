#!/bin/bash

unset GITHUB_TOKEN

# Navigate to repo
cd /workspaces/codespaces-blank/StockLeague

# Add changes
git add -A

# Commit
git commit -m "feat: implement theme-adaptive navbar and fix text contrast on blue backgrounds

- Make navbar background and text color adapt to selected theme
- Update dropdown menus to respect theme CSS variables
- Add white text styling for blue backgrounds
- Fix dropdown text contrast for all themes (dark, light, ocean, forest, sunset)
- Ensure navbar links, dropdowns, and buttons show proper contrast
- Add smooth transitions when theme is changed
- Update hero and CTA sections with white text on blue backgrounds"

echo "✓ Commit complete"
