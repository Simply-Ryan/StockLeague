#!/bin/bash
set -e

echo "🚀 Setting up StockLeague development environment..."
echo ""

# Step 1: Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Step 2: Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Step 3: Upgrade pip
echo "⬆️  Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Step 4: Install requirements
echo "📥 Installing project dependencies (this may take 2-3 minutes)..."
pip install -r requirements.txt

# Step 5: Install dev requirements
echo "🧪 Installing dev dependencies..."
pip install -r dev-requirements.txt

# Step 6: Initialize database if needed
echo "💾 Checking database..."
if [ ! -f "database/stocks.db" ]; then
    echo "🔧 Initializing database..."
    python3 initialize_database.py
else
    echo "✓ Database already exists"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "📌 Next steps:"
echo "   1. Activate the virtual environment: source venv/bin/activate"
echo "   2. Start the development server: python3 app.py"
echo "   3. Open http://localhost:5000 in your browser"
echo ""
echo "💡 To run tests: pytest -v"
echo "💡 To run specific test: pytest tests/test_explore.py -v"
echo ""
