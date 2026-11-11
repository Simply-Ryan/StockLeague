"""Install the StockLeague development environment.

Use this when development dependencies and test tooling are needed. It does
not delete or recreate the local database.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def interpreter() -> Path:
    """Return the project virtual environment interpreter."""
    executable = "Scripts/python.exe" if platform.system() == "Windows" else "bin/python"
    return VENV / executable


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    if sys.version_info < (3, 8):
        print("StockLeague requires Python 3.8 or newer.", file=sys.stderr)
        return 1

    if not interpreter().exists():
        print("Creating .venv...")
        run([sys.executable, "-m", "venv", str(VENV)])

    python = str(interpreter())
    run([python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([python, "-m", "pip", "install", "-r", "requirements.txt"])
    run([python, "-m", "pip", "install", "-r", "dev-requirements.txt"])
    print("Development environment ready.")
    print(f"Run {python} -m pytest -q to execute the test suite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
