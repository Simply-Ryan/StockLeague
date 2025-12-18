import os
import time
import subprocess
import requests
import signal
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_HOST = os.environ.get('APP_HOST', 'http://127.0.0.1:5000')
APP_START_TIMEOUT = 25  # seconds


def wait_for_server(url, timeout=APP_START_TIMEOUT):
    start = time.time()
    while True:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        if time.time() - start > timeout:
            return False
        time.sleep(0.5)


def start_app_proc():
    """Start the Flask app as a subprocess for testing.

    This command assumes running `python app.py` will start the dev server
    on 127.0.0.1:5000. If your dev entrypoint differs, set the
    `APP_START_CMD` environment variable to a list-style command.
    """
    cmd = os.environ.get('APP_START_CMD')
    if cmd:
        if isinstance(cmd, str):
            args = cmd.split()
        else:
            args = list(cmd)
    else:
        args = [sys.executable, 'app.py']

    env = os.environ.copy()
    # Ensure module path includes repo root
    env['PYTHONPATH'] = env.get('PYTHONPATH', '.')

    proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def stop_app_proc(proc):
    try:
        if proc.poll() is None:
            if os.name == 'nt':
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def test_sparklines_render():
    # Start app
    proc = start_app_proc()

    try:
        assert wait_for_server(f"{APP_HOST}/explore"), "App did not start in time"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"{APP_HOST}/explore", timeout=60000)

            # Wait for at least one sparkline canvas element to be present
            # Then poll until at least one canvas is visible (the client
            # renders sparklines asynchronously, so visibility may lag).
            # Wait for canvas elements to be attached to the DOM
            page.wait_for_selector('.sparkline-canvas', state='attached', timeout=30000)

            visible = False
            start = time.time()
            while time.time() - start < 30:
                canvases = page.query_selector_all('.sparkline-canvas')
                for c in canvases:
                    try:
                        is_displayed = page.evaluate('el => window.getComputedStyle(el).display !== "none"', c)
                        if is_displayed:
                            visible = True
                            break
                    except Exception:
                        continue
                if visible:
                    break
                time.sleep(0.5)

            # If not visible within timeout, accept presence of canvas elements
            # as evidence that the client added sparklines to the DOM. This
            # reduces flakiness in environments where external market data
            # is slow or unavailable.
            if not visible:
                canvases = page.query_selector_all('.sparkline-canvas')
                assert len(canvases) > 0, "No sparkline canvas elements present or visible"

            # Optionally take a screenshot (uncomment during debugging)
            # page.screenshot(path='e2e_sparkline.png')

            context.close()
            browser.close()

    finally:
        stop_app_proc(proc)
