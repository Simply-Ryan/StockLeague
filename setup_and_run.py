"""Set up a downloaded StockLeague folder and start the application."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import List


PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"
ENV_FILE = PROJECT_DIR / ".env"
ENV_TEMPLATE = PROJECT_DIR / ".env.example"
APP_URL = "http://127.0.0.1:5000"


def project_python() -> Path:
    """Return the Python executable inside the project environment."""
    relative_path = (
        Path("Scripts") / "python.exe"
        if platform.system() == "Windows"
        else Path("bin") / "python"
    )
    return VENV_DIR / relative_path


def run(command: List[str], *, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a project command and raise a useful error when it fails."""
    return subprocess.run(
        command,
        cwd=str(PROJECT_DIR),
        check=True,
        capture_output=capture_output,
        text=True,
    )


def ensure_environment() -> Path:
    """Create the virtual environment and install the pinned dependencies."""
    interpreter = project_python()
    if not interpreter.exists():
        print("Creating the project environment...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
        interpreter = project_python()

    if not interpreter.exists():
        raise RuntimeError("The virtual environment was created without a Python executable.")

    print("Installing application dependencies...")
    run([str(interpreter), "-m", "pip", "install", "--disable-pip-version-check",
         "-r", str(REQUIREMENTS_FILE)])
    return interpreter


def ensure_configuration() -> None:
    """Create a local environment file without overwriting user settings."""
    if ENV_FILE.exists() or not ENV_TEMPLATE.exists():
        return
    shutil.copyfile(str(ENV_TEMPLATE), str(ENV_FILE))
    print("Created .env from .env.example.")


def open_browser() -> None:
    """Open the app after the development server has had time to start."""
    time.sleep(2.5)
    webbrowser.open(APP_URL)


def main() -> int:
    """Prepare a fresh download and run StockLeague."""
    if sys.version_info < (3, 8):
        print("StockLeague requires Python 3.8 or newer.", file=sys.stderr)
        return 1
    if not REQUIREMENTS_FILE.exists():
        print("requirements.txt was not found in the project folder.", file=sys.stderr)
        return 1

    try:
        ensure_configuration()
        interpreter = ensure_environment()
        print("Starting StockLeague at {}".format(APP_URL))
        threading.Thread(target=open_browser, daemon=True).start()
        run([str(interpreter), "app.py"])
    except subprocess.CalledProcessError as error:
        print("A setup command failed with exit code {}.".format(error.returncode), file=sys.stderr)
        return error.returncode or 1
    except OSError as error:
        print("Could not start StockLeague: {}".format(error), file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
