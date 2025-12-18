#!/bin/bash

unset GITHUB_TOKEN

cd /workspaces/codespaces-blank/StockLeague

git add -A

git commit -m "fix: add missing mode and rules_json columns to leagues table

- Add 'mode' column to leagues table with default 'standard'
- Add 'rules_json' column to leagues table for storing game rules
- Add error handling in create_league route for missing columns
- Import sqlite3 in app.py for exception handling
- Provides graceful fallback when new columns don't exist
- Allows league creation to succeed even with schema differences"

echo "✓ Fixes committed successfully"
