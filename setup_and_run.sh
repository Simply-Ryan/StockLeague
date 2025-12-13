#!/bin/bash
# StockLeague Setup & Run - Mac/Linux Bash Script
# Run this file to automatically set up and run StockLeague

echo ""
echo "========================================"
echo "  StockLeague Setup & Launcher"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo ""
    echo "Please install Python 3.8+ from https://www.python.org/downloads/"
    echo "Or use Homebrew on Mac: brew install python3"
    echo ""
    read -p "Press any key to exit..."
    exit 1
fi

# Show Python version
echo "Python is installed:"
python3 --version
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run the setup script
echo "Launching StockLeague Setup & Launcher..."
python3 "$SCRIPT_DIR/setup_and_run.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "Setup failed. Please check the error above."
    read -p "Press any key to exit..."
    exit 1
fi
