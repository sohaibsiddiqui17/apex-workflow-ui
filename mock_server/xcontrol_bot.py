"""
Apex Workflow X-Control — Playwright Bot
=========================================
Scrapes the Import Confirm → Pending tab from the mock frontend and
posts every row to POST /api/import-confirm/bulk.

Prerequisites
-------------
  pip install playwright python-dotenv
  playwright install chromium

Environment (.env in mock_server/ or the parent directory)
-----------------------------------------------------------
  XCONTROL_USER=your_username
  XCONTROL_PASS=your_password
  XCONTROL_URL=http://localhost:8090        # default
  HEADLESS=true                             # set false to watch the browser

Run
---
  cd mock_server
  python xcontrol_bot.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

# Load .env from mock_server/ first, then parent dir
_here = Path(__file__).parent
load_dotenv(_here / ".env")
load_dotenv(_here.parent / ".env")

BASE_URL: str = os.environ.get("XCONTROL_URL", "http://localhost:8090").rstrip("/")
USERNAME: str = os.environ.get("XCONTROL_USER", "")
PASSWORD: str = os.environ.get("XCONTROL_PASS", "")
HEADLESS: bool = os.environ.get("HEADLESS", "true").lower() not in ("false", "0", "no")

# Mapping from IC_PENDING_DATA JS keys → DB column names
JS_KEY_TO_DB: Dict[str, str] = {
    "status":     "status",
    "abiStatus":  "abi_query_status",
    "abiMatch":   "abi_query_match",
    "uld":        "uld_no",
    "customer":   "hawb_customer",
    "mno":        "mawb",
    "hno":        "hawb",
    "eta":        "eta",
    "pol":        "pol",
    "pod":        "pod",
    "firm":       "firm_code",
    "flight":     "flight_no",
    "addr":       "address",
    "lfd":        "last_free_date",
    "wt":         "wt",
    "scStatus":   "sc_job_status",
    "opRem":      "op_remarks",
    "scJob":      "sc_job_no",
    "preAlert":   "pre_alert_date",
    "isOvs":      "is_ovs_agent",
    "qSend":      "query_send_date",
    "qUpdate":    "query_update_date",
    "operator":   "operator",
    "tags":       "tags",
}


# ─────────────────────────────────────────────────────────────────────────────
# Logger
# ─────────────────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def log_section(title: str) -> None:
    bar = "─" * 60
    print(f"\n{bar}", flush=True)
    print(f"[{ts()}] {title}", flush=True)
    print(bar, flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Verify credentials via API before opening browser
# ─────────────────────────────────────────────────────────────────────────────

def api_login(username: str, password: str) -> str:
    log_section("STEP 1 — API credential check")
    url = f"{BASE_URL}/api/login"
    log(f"POST {url}")
    try:
        resp = requests.post(url, json={"username": username, "password": password}, timeout=10)
    except requests.ConnectionError:
        log(f"ERROR: Cannot connect to {BASE_URL}. Is the server running?")
        sys.exit(1)

    if resp.status_code == 401:
        log("ERROR: Invalid credentials (401). Check XCONTROL_USER / XCONTROL_PASS in .env")
        sys.exit(1)
    resp.raise_for_status()

    data = resp.json()
    token = data.get("token", "")
    log(f"Login OK — token prefix: {token[:16]}…")
    return token


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Browser login
# ─────────────────────────────────────────────────────────────────────────────

def browser_login(page: Page, username: str, password: str) -> None:
    log_section("STEP 2 — Browser login")
    login_url = f"{BASE_URL}/login.html"
    log(f"Navigating to {login_url}")
    page.goto(login_url, wait_until="domcontentloaded")
    page.wait_for_timeout(600)

    # Fill credentials
    page.fill("#username", username)
    log(f"Filled #username = {username!r}")
    page.fill("#password", password)
    log("Filled #password = ****")

    # Click login
    login_btn = page.locator("button[type=submit]").first
    login_btn.click()
    log("Clicked login button")
    page.wait_for_timeout(800)

    # Navigate directly to app (mock login page doesn't redirect on its own)
    app_url = f"{BASE_URL}/index.html"
    log(f"Navigating to main app: {app_url}")
    page.goto(app_url, wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    log("Main app loaded")


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Navigate to Import Confirm → Pending tab
# ─────────────────────────────────────────────────────────────────────────────

def navigate_to_import_confirm(page: Page) -> None:
    log_section("STEP 3 — Navigate to Import Confirm → Pending")
    # Use JS to trigger the nav function (more reliable than clicking coordinates)
    page.evaluate("() => navClick(16, 'Import Confirm')")
    log("Called navClick(16, 'Import Confirm')")
    page.wait_for_timeout(800)

    # Ensure Pending tab (ic-panel-0) is active
    page.evaluate("() => { const tabs = document.querySelectorAll('.ic-inner-tab'); if (tabs[0]) tabs[0].click(); }")
    page.wait_for_timeout(400)

    # Confirm table is populated
    row_count = page.evaluate("() => document.querySelectorAll('#ic-tbody tr').length")
    log(f"Import Confirm Pending tab: {row_count} rows visible in DOM")


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Extract all rows (all pages)
# ─────────────────────────────────────────────────────────────────────────────

def extract_all_rows(page: Page) -> List[Dict[str, Any]]:
    log_section("STEP 4 — Extract rows from all pages")

    # Primary strategy: pull IC_PENDING_DATA directly from JS runtime.
    # This is authoritative for the mock frontend (all rows, no pagination gaps).
    js_rows: List[Dict] = page.evaluate("""
        () => {
            if (typeof IC_PENDING_DATA !== 'undefined' && Array.isArray(IC_PENDING_DATA)) {
                return IC_PENDING_DATA;
            }
            return null;
        }
    """)

    if js_rows is not None:
        log(f"Extracted {len(js_rows)} rows from IC_PENDING_DATA (JS runtime)")
        return js_rows

    # Fallback: DOM scraping across pages (for adapting to the real portal)
    log("IC_PENDING_DATA not found — falling back to DOM scraping")
    return _dom_scrape_all_pages(page)


def _dom_scrape_all_pages(page: Page) -> List[Dict[str, Any]]:
    """
    Scrapes the table DOM row-by-row, handling pagination.
    Reads column names from #hdr-name-row and maps cells to those names.
    """
    all_rows: List[Dict[str, Any]] = []
    page_num = 0

    while True:
        page_num += 1
        rows_on_page = _scrape_current_page(page)
        all_rows.extend(rows_on_page)
        log(f"  Page {page_num}: {len(rows_on_page)} rows (total so far: {len(all_rows)})")

        # Check pagination info
        pg_info = page.locator("#pg-info").text_content() or ""
        log(f"  Pagination: {pg_info.strip()}")

        # Try to go to next page
        next_btn = page.locator(".pg-btn", has_text="Next")
        if next_btn.count() == 0:
            break
        is_disabled = next_btn.get_attribute("disabled")
        if is_disabled is not None:
            break

        # Parse "Page X of Y" to know when to stop
        import re
        m = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", pg_info)
        if m and int(m.group(1)) >= int(m.group(2)):
            break

        next_btn.click()
        page.wait_for_timeout(500)

    return all_rows


def _scrape_current_page(page: Page) -> List[Dict[str, Any]]:
    # Get column names from header row (skip checkbox col)
    col_names: List[str] = page.evaluate("""
        () => {
            const ths = Array.from(document.querySelectorAll('#hdr-name-row th'));
            return ths.slice(1).map(th => th.innerText.trim());
        }
    """)

    rows_data: List[List[str]] = page.evaluate("""
        () => {
            const trs = Array.from(document.querySelectorAll('#ic-tbody tr'));
            return trs.map(tr => {
                const tds = Array.from(tr.querySelectorAll('td'));
                return tds.slice(1).map(td => td.innerText.trim());
            });
        }
    """)

    result = []
    for cells in rows_data:
        row: Dict[str, Any] = {}
        for i, col in enumerate(col_names):
            row[col] = cells[i] if i < len(cells) else ""
        result.append(row)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Map JS keys → DB column names
# ─────────────────────────────────────────────────────────────────────────────

def map_rows(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    log_section("STEP 5 — Map field names to DB columns")
    mapped: List[Dict[str, Any]] = []
    for raw in raw_rows:
        row: Dict[str, Any] = {}
        for js_key, db_col in JS_KEY_TO_DB.items():
            val = raw.get(js_key)
            if val is not None and str(val).strip() not in ("", "nan", "None"):
                row[db_col] = str(val).strip()
        if row.get("mawb"):
            mapped.append(row)
    log(f"Mapped {len(mapped)} rows with valid MAWB")
    return mapped


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — POST rows to bulk endpoint
# ─────────────────────────────────────────────────────────────────────────────

def post_bulk(rows: List[Dict[str, Any]], token: str) -> Dict[str, Any]:
    log_section("STEP 6 — POST rows to /api/import-confirm/bulk")
    url = f"{BASE_URL}/api/import-confirm/bulk"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    log(f"POST {url}  ({len(rows)} rows)")
    t0 = time.monotonic()
    resp = requests.post(url, json=rows, headers=headers, timeout=30)
    elapsed = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    log(f"Response ({elapsed:.2f}s): upserted={data.get('upserted')}  "
        f"skipped={data.get('skipped')}  errors={len(data.get('errors', []))}")
    if data.get("errors"):
        for err in data["errors"][:5]:
            log(f"  ! {err}")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log_section("Apex Workflow X-Control Bot — starting")
    log(f"Target:   {BASE_URL}")
    log(f"Username: {USERNAME or '(not set — check .env)'}")
    log(f"Headless: {HEADLESS}")

    if not USERNAME or not PASSWORD:
        log("ERROR: XCONTROL_USER and XCONTROL_PASS must be set in .env")
        sys.exit(1)

    # Step 1 — API login
    token = api_login(USERNAME, PASSWORD)

    # Steps 2–5 — Browser
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS, slow_mo=50 if not HEADLESS else 0)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        # Capture console errors
        page.on("console", lambda msg: (
            log(f"  [browser:{msg.type}] {msg.text}") if msg.type == "error" else None
        ))

        try:
            browser_login(page, USERNAME, PASSWORD)
            navigate_to_import_confirm(page)
            raw_rows = extract_all_rows(page)
        finally:
            context.close()
            browser.close()

    # Steps 5–6 — Map + POST
    db_rows = map_rows(raw_rows)
    result = post_bulk(db_rows, token)

    log_section("Done")
    log(f"Total scraped : {len(raw_rows)}")
    log(f"Total mapped  : {len(db_rows)}")
    log(f"Upserted      : {result.get('upserted')}")
    log(f"Skipped       : {result.get('skipped')}")


if __name__ == "__main__":
    main()
