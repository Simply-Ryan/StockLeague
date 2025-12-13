# StockLeague - One-Click Setup & Run Guide

This guide explains how to set up and run StockLeague without using the terminal.

## ⚠️ Prerequisites

Before you can run StockLeague, you need to install **Python 3.8 or higher**:

### Windows
1. Go to https://www.python.org/downloads/
2. Click "Download Python 3.x.x"
3. Run the installer
4. **IMPORTANT**: Check the box that says "Add Python to PATH" during installation
5. Click "Install Now"

### Mac
1. Go to https://www.python.org/downloads/
2. Click "Download Python 3.x.x for macOS"
3. Run the installer and follow the prompts
4. Or use Homebrew: `brew install python3`

## 🚀 Running StockLeague

### Windows Users

**Option 1: Double-Click (Easiest)**
1. Find the file named `setup_and_run.bat` in the StockLeague folder
2. Double-click it
3. A setup window will appear
4. Click "Start Setup & Launch"
5. Wait for the setup to complete (may take 2-3 minutes on first run)
6. Your browser will automatically open to http://localhost:5000

**Option 2: Right-Click Method**
1. Right-click on `setup_and_run.bat`
2. Select "Run as Administrator" (if prompted)
3. Follow the same steps as Option 1

### Mac Users

**Option 1: Make Script Executable (One-Time Setup)**
1. Open Terminal
2. Copy and paste this command:
   ```
   chmod +x ~/path/to/StockLeague/setup_and_run.sh
   ```
3. Replace `~/path/to/StockLeague/` with the actual path to your StockLeague folder
4. Press Enter
5. Now you can double-click `setup_and_run.sh` to run it

**Option 2: Always Use Terminal**
1. Open Terminal
2. Navigate to the StockLeague folder:
   ```
   cd ~/path/to/StockLeague/
   ```
3. Run the script:
   ```
   bash setup_and_run.sh
   ```

### What Happens During Setup

1. ✓ Checks Python version
2. ✓ Creates a virtual environment (isolated Python installation for this project)
3. ✓ Installs all required dependencies from `requirements.txt`
4. ✓ Starts the Flask web server
5. ✓ Opens StockLeague in your default browser

## 🌐 Accessing the App

Once setup is complete, StockLeague will be available at:
```
http://localhost:5000
```

The browser should open automatically. If it doesn't, copy and paste the URL above into your browser's address bar.

## 🛑 Stopping the App

### Windows
1. Find the command prompt/terminal window that's running the app
2. Press `Ctrl + C`

### Mac
1. Find the Terminal window that's running the app
2. Press `Ctrl + C`

Or simply close the terminal window.

## 🔧 Troubleshooting

### "Python is not installed"
- You need to install Python 3.8 or higher from https://www.python.org/downloads/
- On Windows, make sure to check "Add Python to PATH" during installation
- After installing Python, close and reopen the setup script

### "Requirements.txt not found"
- Make sure you're running the script from the StockLeague folder
- All files should be in the same directory

### Port 5000 is already in use
- Close any other Flask/Python applications running
- Or edit `app.py` and change the port number at the bottom

### On Mac: "Permission denied" error
- Run this command in Terminal:
  ```
  chmod +x /path/to/setup_and_run.sh
  ```
- Then try again

### Browser doesn't open automatically
- Manually go to http://localhost:5000 in your browser
- If it says "connection refused", wait a few seconds and try again

### Setup is slow
- First-time setup takes 2-3 minutes to install dependencies
- Subsequent runs will be much faster
- Check your internet connection

## 📁 What Gets Created

When you run the setup, these files/folders are created:

```
StockLeague/
├── venv/              ← Virtual environment (Python packages isolated here)
├── database/          ← Where your data is stored
│   └── stocks.db      ← SQLite database
├── flask_session/     ← Session data
├── setup_and_run.py   ← Main setup script
├── setup_and_run.bat  ← Windows shortcut
├── setup_and_run.sh   ← Mac/Linux shortcut
└── requirements.txt   ← List of dependencies
```

## 🔄 Restarting the App

Just run `setup_and_run.bat` (Windows) or `setup_and_run.sh` (Mac) again. It will reuse the existing virtual environment, so it will be much faster.

## 💾 Database & Data

All your portfolio data, trades, messages, and settings are stored in:
```
StockLeague/database/stocks.db
```

This file is preserved between runs, so you won't lose any data.

## 🌍 Accessing from Another Computer

By default, StockLeague only works on your local computer. To access it from another computer on the network:

1. Edit `app.py` and find the line `socketio.run(app, ...)`
2. Change it from `host='localhost'` to `host='0.0.0.0'`
3. Restart the app
4. Find your computer's IP address:
   - Windows: Run `ipconfig` in Command Prompt, look for "IPv4 Address"
   - Mac: System Preferences → Network → look for IP Address
5. Other computers can access: `http://YOUR_IP:5000`

## 📞 Support

If you encounter issues:
1. Check the "Troubleshooting" section above
2. Make sure Python 3.8+ is installed
3. Try running in a different browser (Chrome, Firefox, Safari)
4. Delete the `venv` folder and run setup again for a fresh start

## 📝 Notes

- The app runs locally on your computer
- No internet connection required after setup (Finnhub API calls do require internet)
- All data is stored locally in your database folder
- The virtual environment is isolated and won't affect other Python projects

---

**Enjoy StockLeague! Happy trading! 📈**
