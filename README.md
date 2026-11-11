# StockLeague

StockLeague is a Flask paper trading application. Users trade with virtual cash, manage portfolios, follow market news, and compete in leagues.

## Requirements

- Python 3.11 or newer is recommended. Python 3.8 remains the minimum supported version.
- Internet access is needed for market data and news.
- Git is optional.

## Windows quick start

After extracting the ZIP file, open the project folder and double-click:

`run_stockleague.bat`

The launcher creates `.venv` if needed, installs `requirements.txt`, creates `.env` from `.env.example` without replacing an existing file, starts the database through the application startup, launches Flask, and opens http://127.0.0.1:5000.

The only prerequisite is Python 3.8 or newer. If Python is not installed, download it from https://www.python.org/downloads/ and enable `Add Python to PATH`.

Stop the server with `Ctrl+C`.

## Manual setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

For Linux or macOS, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

Copy `.env.example` to `.env` when local configuration is needed. The application creates and upgrades its SQLite database during startup. Do not commit `.env` or database files.

## Main pages

| Page | Purpose |
| --- | --- |
| `/` | Public home page |
| `/register` | Create an account |
| `/login` | Sign in |
| `/dashboard` | View the active portfolio |
| `/trade` | Look up quotes and trade stocks |
| `/explore` | Browse stocks |
| `/news` | Read market news |
| `/leagues` | Create or join leagues |

Most pages require an authenticated session.

## Development

Install development dependencies when working on tests:

```powershell
.\.venv\Scripts\python.exe -m pip install -r dev-requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Run a focused test file with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_trading.py -q
```

The Playwright browser is required only for end-to-end tests:

```powershell
.\.venv\Scripts\python.exe -m playwright install
```

## Project layout

- `app.py`: legacy application entrypoint and remaining routes
- `app_factory.py`: application factory and configuration
- `blueprints/`: modular route groups
- `database/`: SQLite access and schema upgrades
- `templates/`: Jinja templates
- `static/`: CSS and JavaScript
- `tests/`: automated tests
- `run_stockleague.bat`: recommended Windows launcher

See [DEV_SETUP.md](DEV_SETUP.md) for development details and troubleshooting.
