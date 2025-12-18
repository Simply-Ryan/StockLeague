# 🚀 Development Environment Setup Guide

This guide walks you through setting up your local development environment for StockLeague.

## Prerequisites

- **Python 3.8+** installed on your system
- Git (to clone the repo - already done ✓)

## Quick Start (Linux/Mac)

### 1. Create and activate a virtual environment

```bash
cd /workspaces/codespaces-blank/StockLeague

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### 2. Upgrade pip and install dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r dev-requirements.txt
```

This will install:
- **Flask & Flask-SocketIO** - Web framework and real-time features
- **yfinance** - Stock market data
- **pytest** - Testing framework
- **playwright** - E2E testing browser automation
- **redis** - (optional) For caching enhancements
- All other dependencies from `requirements.txt`

### 3. Initialize the database

The database will be created automatically when you first run the app, or you can initialize it manually:

```bash
python3 initialize_database.py
```

This creates `database/stocks.db` with all necessary tables.

### 4. Create a `.env` file (optional but recommended)

```bash
cp .env.example .env
```

You can edit `.env` to customize settings. Default values work fine for local development.

### 5. Run the application

```bash
python3 app.py
```

You should see output like:
```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

Open your browser and navigate to: **http://localhost:5000**

## What's Running

When you start the app, you get:
- ✅ Flask web server on port 5000
- ✅ SQLite database in `database/stocks.db`
- ✅ Real-time Socket.IO connections
- ✅ Static files served from `static/`
- ✅ Jinja2 template rendering

## Common Development Tasks

### Run tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_explore.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Run a specific test
```bash
pytest tests/test_explore.py::test_explore_page_renders -v
```

### Install Playwright browsers (for E2E tests)

```bash
playwright install
```

### Check the database schema

```bash
python3 check_schema.py
```

### View database contents

```bash
python3 check_db.py
```

### Reset the database

```bash
rm database/stocks.db
python3 initialize_database.py
```

## Project Structure

```
StockLeague/
├── app.py                    # Main Flask app
├── helpers.py               # Market data helpers (lookup, get_chart_data, etc.)
├── league_modes.py          # League game mode logic
├── league_rules.py          # League rules engine
├── utils.py                 # Utility functions
│
├── database/
│   ├── db_manager.py        # Database connection & CRUD operations
│   └── stocks.db            # SQLite database (created on first run)
│
├── blueprints/              # Flask blueprints (optional modularization)
│   ├── api_bp.py
│   ├── auth_bp.py
│   ├── portfolio_bp.py
│   └── explore_bp.py
│
├── templates/               # Jinja2 HTML templates
│   ├── layout.html          # Main layout
│   ├── index.html
│   ├── explore.html
│   ├── league_detail.html
│   └── ... more templates
│
├── static/                  # CSS, JavaScript, images
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── app.js
│   │   ├── realtime.js
│   │   └── leaderboards.js
│   └── avatars/
│
├── tests/                   # Pytest test files
│   ├── test_explore.py
│   ├── test_leaderboard.py
│   └── test_league_admin.py
│
└── requirements.txt         # Python dependencies
```

## Environment Variables

Key variables in `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | `fallback-secret-key` | Session encryption (⚠️ change in production) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache (optional) |
| `FLASK_ENV` | `development` | Flask environment |
| `FLASK_DEBUG` | `True` | Enable debug mode |

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
You probably forgot to activate your virtual environment.
```bash
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### Database locked errors
This happens when multiple processes access the SQLite database. Kill any other running instances:
```bash
pkill -f "python3 app.py"
```

### Port 5000 already in use
Find what's using it:
```bash
lsof -i :5000  # Linux/Mac
netstat -ano | findstr :5000  # Windows
```

Then stop it or use a different port:
```bash
python3 app.py --port 5001
```

### Playwright browsers not installed
Install them:
```bash
playwright install
```

## Next Steps

After setup is complete, check the [TODO list](../PROJECT_REVIEW.md#4-future-features--prioritized) for what features to work on next!

Key priorities:
1. 🔴 **High**: Cache `/api/chart/<symbol>` server-side (5-30 min)
2. 🔴 **High**: Redis caching & session store
3. 🟡 **Medium**: Admin portfolio_resets UI with CSV export
4. 🟡 **Medium**: Playwright E2E tests

## Getting Help

- Check `PROJECT_REVIEW.md` for architectural overview and known issues
- Check `SETUP_GUIDE.md` for user-facing setup instructions
- Run tests to verify your setup: `pytest -v`
- Check individual files for inline documentation

Happy coding! 🎉
