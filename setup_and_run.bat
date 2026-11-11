@echo off
setlocal
cd /d "%~dp0"

call run_stockleague.bat
exit /b %errorlevel%
