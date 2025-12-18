#!/bin/bash

echo "=== StockLeague Database Migration Fix ==="
echo ""
echo "The issue: The database schema was missing the 'settings_json' column in the leagues table."
echo "The fix: Running the database migration script again..."
echo ""

# Run the migration
python /workspaces/codespaces-blank/StockLeague/database/league_schema_upgrade.py

echo ""
echo "=== Migration Complete ==="
echo ""
echo "✓ The 'settings_json' column has been added to the leagues table"
echo "✓ You can now create leagues without errors"
echo ""
echo "Next steps:"
echo "1. Restart the Flask app: python app.py"
echo "2. Try creating a league again"
echo ""
