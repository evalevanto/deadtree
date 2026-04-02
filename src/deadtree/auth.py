"""Overleaf authentication via browser login and cookie persistence."""

import json
import os
import re
from pathlib import Path

import requests


def login(session_dir: Path) -> None:
    """Open a browser for Overleaf login, save session cookies."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Playwright is required for login.\n"
            "Install: pip install 'deadtree[login]' && playwright install chromium"
        )

    os.makedirs(session_dir, mode=0o700, exist_ok=True)
    cookie_file = session_dir / "cookies.json"

    with sync_playwright() as p:
        user_data_dir = str(session_dir / "browser_profile")
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.overleaf.com/login")

        print("Log in via the browser window.")
        print("Waiting for you to reach the project dashboard (5 min timeout)...")

        try:
            page.wait_for_url("**/project**", timeout=300_000)
        except Exception:
            if "/project" not in (page.url if not page.is_closed() else ""):
                print("Login cancelled or timed out.")
                context.close()
                return

        print("Login successful!")
        cookies = context.cookies()
        fd = os.open(cookie_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"Session saved to {cookie_file}")
        context.close()


def get_session(session_dir: Path) -> requests.Session:
    """Build a requests.Session from saved cookies."""
    cookie_file = session_dir / "cookies.json"
    if not cookie_file.exists():
        raise SystemExit(
            "No saved session. Run: deadtree login"
        )

    cookies = json.loads(cookie_file.read_text())
    session = requests.Session()
    for c in cookies:
        session.cookies.set(
            c["name"], c["value"],
            domain=c.get("domain", ""),
            path=c.get("path", "/"),
        )
    return session


def get_csrf(session: requests.Session, project_id: str) -> str:
    """Fetch CSRF token from the Overleaf project page."""
    r = session.get(f"https://www.overleaf.com/project/{project_id}")
    if "login" in r.url:
        raise SystemExit("Session expired. Run: deadtree login")
    r.raise_for_status()

    m = re.search(r'<meta\s+name="ol-csrfToken"\s+content="([^"]+)"', r.text)
    if not m:
        raise SystemExit("Could not get CSRF token. Run: deadtree login")
    return m.group(1)
