#!/bin/bash

# Run the database migration to add missing columns
echo "Running database migration to fix league schema..."
python database/league_schema_upgrade.py

echo ""
echo "✓ Migration complete. The settings_json column has been added to the leagues table."
echo "You can now try creating a league again."
