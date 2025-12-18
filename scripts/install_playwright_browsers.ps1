# PowerShell helper: install Playwright browser binaries
# Run after `pip install -r dev-requirements.txt`

python -m playwright install chromium
# Optionally install firefox and webkit
# python -m playwright install firefox
# python -m playwright install webkit
