# Running StockLeague

## Windows

1. Install Python 3.8 or newer from https://www.python.org/downloads/.
2. During installation, enable the option to add Python to PATH.
3. Open the StockLeague folder.
4. Double-click `run_stockleague.bat`.

The launcher performs the remaining setup automatically. It creates the project environment, installs dependencies, creates missing local configuration, starts the app, and opens the browser. It does not replace an existing `.env` or database.

You can also run it from PowerShell:

```powershell
.\run_stockleague.bat
```

The script creates `.venv`, installs the pinned dependencies, and starts the server. Visit http://127.0.0.1:5000.

## Other platforms

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## Stop and restart

Press `Ctrl+C` in the server window. Run the same launcher again to restart. Existing database data remains in the local database file.

## If setup fails

Run the commands manually with the project interpreter:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

For development, testing, environment variables, and database notes, see [DEV_SETUP.md](DEV_SETUP.md).
