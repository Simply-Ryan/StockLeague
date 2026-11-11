# StockLeague development setup

This guide describes the current local development workflow. Commands assume PowerShell on Windows. Use the equivalent `.venv/bin/python` path on Linux or macOS.

## First run

From the StockLeague directory:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

The app is available at http://127.0.0.1:5000. The database is SQLite and is created or upgraded at startup.

For the simplest repeatable Windows workflow, run:

```powershell
.\run_stockleague.bat
```

This command always uses the project-local `.venv`, which prevents the common `ModuleNotFoundError` caused by installing packages into a different Python installation.

## Configuration

The application loads `.env` when present. Keep credentials and local settings there. The repository includes `.env.example` as a reference. Never commit `.env`, API keys, session files, or SQLite databases.

Market data uses the configured providers in `helpers.py`. News uses Yahoo Finance first and Google News RSS as a fallback. Some pages can still render without live market data, but quote and news content requires internet access.

## Tests and checks

Run the syntax check:

```powershell
.\.venv\Scripts\python.exe -m compileall -q .
```

Run the full test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_trading.py tests\integration\test_concurrent_trades.py -q
```

Install Playwright browsers only when running browser tests:

```powershell
.\.venv\Scripts\python.exe -m playwright install
```

## Database notes

The local database is ignored by Git. Back it up before testing migrations. Do not delete it unless you intentionally want to reset local accounts, trades, leagues, and settings.

Useful read-only checks include:

```powershell
.\.venv\Scripts\python.exe check_schema.py
.\.venv\Scripts\python.exe check_db.py
```

## Common problems

### APScheduler or another package is missing

Use the project interpreter rather than the system interpreter:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

### Port 5000 is already in use

Find the process:

```powershell
Get-NetTCPConnection -LocalPort 5000 -State Listen
```

Stop only the specific process after confirming its PID:

```powershell
Stop-Process -Id <PID>
```

### A page appears stale

Restart Flask and hard refresh the browser with `Ctrl+Shift+R`. Static assets include a cache version in the shared layout.

### Dependency installation fails

Confirm that the project is using a supported Python version, then upgrade packaging tools:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
