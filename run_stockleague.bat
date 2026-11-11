@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if not errorlevel 1 goto run_with_python

where py >nul 2>&1
if errorlevel 1 (
    echo Python was not found.
    echo Install Python 3.8 or newer from https://www.python.org/downloads/
    echo Enable "Add Python to PATH" during installation, then run this file again.
    pause
    exit /b 1
)

py -3 setup_and_run.py
if errorlevel 1 (
    echo.
    echo StockLeague could not be started.
    pause
    exit /b 1
)
exit /b 0

:run_with_python
python setup_and_run.py
if errorlevel 1 (
    echo.
    echo StockLeague could not be started.
    pause
    exit /b 1
)
