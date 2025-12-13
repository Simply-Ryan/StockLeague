@echo off
REM StockLeague Setup & Run - Windows Batch Script
REM Double-click this file to automatically set up and run StockLeague

echo.
echo ========================================
echo  StockLeague Setup & Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Show Python version
echo Python is installed:
python --version
echo.

REM Run the setup script
echo Launching StockLeague Setup & Launcher...
python "%~dp0setup_and_run.py"

if %errorlevel% neq 0 (
    echo.
    echo Setup failed. Press any key to exit...
    pause
    exit /b 1
)
