# Quick start

From PowerShell:

```powershell
Set-Location C:\Programming\Visual_Studio_Code\WebApps\StockLeague
.\run_stockleague.bat
```

Open http://127.0.0.1:5000, create an account, and sign in. The application starts with a personal portfolio and virtual cash.

Important routes:

- `/home`: public landing page
- `/dashboard`: portfolio dashboard
- `/trade`: quote lookup and trading
- `/news`: market news
- `/leagues`: leagues and competitions

Press `Ctrl+C` to stop the server. If a dependency is missing, use the commands in [DEV_SETUP.md](DEV_SETUP.md) with `.venv\Scripts\python.exe`.
