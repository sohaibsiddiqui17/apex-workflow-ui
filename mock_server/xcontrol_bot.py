"""
Apex Workflow X-Control — Playwright Bot
=========================================

Drives the four-layer X-Control stack:

    login page  ->  HPlus shell  ->  iframe[name="iframe16"]  ->  Element UI grid

Because the mock now reproduces that structure class-for-class, ONE driver
handles both targets. Only the URLs differ:

    --target mock         http://localhost:8090          (default)
    --target production   https://www.apexworkflow.com

Extraction rules that matter on both:

  * Data rows live in ``.el-table__body-wrapper tr.el-table__row``. Scoping to
    the body wrapper is mandatory — Element UI renders a SECOND full copy of
    every row inside ``.el-table__fixed`` for the frozen checkbox column, so an
    unscoped query returns twice the rows, half of them blank.
  * The selection column is inverted between the two copies: it is ``is-hidden``
    in the main table and visible in the fixed clone. Read data from the main
    table; click row checkboxes in the fixed clone.
  * Columns are identified by header text, never by ``el-table_1_column_N``,
    which is positional and shifts whenever a column is added or reordered.

Prerequisites
-------------
  pip install playwright python-dotenv requests
  playwright install chromium

Environment (.env in mock_server/ or the parent directory)
-----------------------------------------------------------
  XCONTROL_USER=your_username
  XCONTROL_PASS=your_password
  XCONTROL_URL=http://localhost:8090        # overrides the target's base URL
  HEADLESS=true                             # set false to watch the browser

Run
---
  cd mock_server
  python xcontrol_bot.py                    # against the mock
  python xcontrol_bot.py --target production --no-ingest
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from playwright.sync_api import FrameLocator, Page, TimeoutError as PWTimeout, sync_playwright

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

_here = Path(__file__).parent
load_dotenv(_here / ".env")
load_dotenv(_here.parent / ".env")

HEADLESS: bool = os.environ.get("HEADLESS", "true").lower() not in ("false", "0", "no")

# Menu indices are identical on both targets — they come from the real portal.
MENU_IMPORT_CONFIRM = 16
MENU_UPDATE_ATD_ATA = 2


class Target:
    """Everything that differs between the mock and the real portal."""

    def __init__(self, name: str, base: str, login_path: str, shell_path: str,
                 has_login_api: bool):
        self.name = name
        self.base = base.rstrip("/")
        self.login_path = login_path
        self.shell_path = shell_path
        self.has_login_api = has_login_api

    @property
    def login_url(self) -> str:
        return f"{self.base}{self.login_path}"

    @property
    def shell_url(self) -> str:
        return f"{self.base}{self.shell_path}"


TARGETS = {
    "mock": Target(
        name="mock",
        base=os.environ.get("XCONTROL_URL", "http://localhost:8090"),
        login_path="/login.html",
        shell_path="/index.html",
        has_login_api=True,
    ),
    "production": Target(
        name="production",
        base=os.environ.get("XCONTROL_URL", "https://www.apexworkflow.com"),
        login_path="/login",
        shell_path="/",
        has_login_api=False,
    ),
}


# Header text (as rendered in the grid) -> database column.
# Mirrors IC_COL_MAP in main.py so scraping, Excel upload and bulk ingest all
# normalise the same way.
HEADER_TO_DB: Dict[str, str] = {
    "status": "status",
    "abi query status": "abi_query_status",
    "abi query match": "abi_query_match",
    "tags": "tags",
    "uld#": "uld_no",
    "hawb customer / account code / cid / gid": "hawb_customer",
    "hawb customer": "hawb_customer",
    "m#": "mawb",
    "h#": "hawb",
    "eta": "eta",
    "pol": "pol",
    "pod": "pod",
    "airline": "airline",
    "firm code": "firm_code",
    "flight no": "flight_no",
    "dest handing office": "dest_handling_office",
    "dest handling office": "dest_handling_office",
    "dest gateway office": "dest_gateway_office",
    "address": "address",
    "last free date": "last_free_date",
    "wt": "wt",
    "sc job status": "sc_job_status",
    "op remarks": "op_remarks",
    "sc job no": "sc_job_no",
    "pre-alert date": "pre_alert_date",
    "dest cs": "dest_cs",
    "isovsagent": "is_ovs_agent",
    "query send date": "query_send_date",
    "query update date": "query_update_date",
    "operator": "operator",
}


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

# Windows consoles default to cp1252; force UTF-8 so log output never dies
# on a non-ASCII character in scraped data.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def log_section(title: str) -> None:
    bar = "-" * 62
    print(f"\n{bar}", flush=True)
    print(f"[{ts()}] {title}", flush=True)
    print(bar, flush=True)


# -----------------------------------------------------------------------------
# Step 1 — credential check (mock only; production has no such endpoint)
# -----------------------------------------------------------------------------

def api_login(target: Target, username: str, password: str) -> str:
    log_section("STEP 1 — API credential check")
    if not target.has_login_api:
        log(f"Target '{target.name}' has no /api/login — skipping, browser login will verify")
        return ""

    url = f"{target.base}/api/login"
    log(f"POST {url}")
    try:
        resp = requests.post(url, json={"username": username, "password": password}, timeout=10)
    except requests.ConnectionError:
        log(f"ERROR: cannot connect to {target.base}. Is the mock backend running?")
        log("       cd mock_server && uvicorn main:app --port 8090 --reload")
        sys.exit(1)

    if resp.status_code == 401:
        log("ERROR: invalid credentials (401). Check XCONTROL_USER / XCONTROL_PASS in .env")
        sys.exit(1)
    resp.raise_for_status()

    token = resp.json().get("token", "")
    log(f"Login OK — token prefix: {token[:16]}...")
    return token


# -----------------------------------------------------------------------------
# Step 2 — browser login (layer 1 -> layer 2)
# -----------------------------------------------------------------------------

def browser_login(page: Page, target: Target, username: str, password: str) -> None:
    log_section("STEP 2 — Browser login")
    log(f"Navigating to {target.login_url}")
    page.goto(target.login_url, wait_until="domcontentloaded")

    page.wait_for_selector("#username", timeout=15_000)
    page.fill("#username", username)
    log(f"Filled #username = {username!r}")
    page.fill("#password", password)
    log("Filled #password = ****")

    # Production's control is <button type="button" id="login">, not a submit
    # button. #login exists on both targets, so this one selector covers them.
    page.click("#login")
    log("Clicked #login")

    # The login page fans the token out to ~100 hidden SSO frames before it
    # redirects, so wait for the shell's own markup rather than a fixed sleep.
    try:
        page.wait_for_selector("#side-menu", timeout=30_000)
        log("Shell loaded — ul#side-menu present")
    except PWTimeout:
        log(f"Shell did not appear; navigating directly to {target.shell_url}")
        page.goto(target.shell_url, wait_until="domcontentloaded")
        page.wait_for_selector("#side-menu", timeout=30_000)

    menu_items = page.locator("a.J_menuItem").count()
    log(f"Menu ready — {menu_items} J_menuItem entries")


# -----------------------------------------------------------------------------
# Step 3 — open a module and enter its iframe (layer 2 -> layers 3/4)
# -----------------------------------------------------------------------------

def open_module(page: Page, index: int, label: str) -> FrameLocator:
    log_section(f"STEP 3 — Open '{label}' (menu index {index})")

    link = page.locator(f'a.J_menuItem[data-index="{index}"]')
    if link.count() == 0:
        raise RuntimeError(f"No menu item with data-index={index} — menu layout changed?")

    # The item may sit inside a collapsed accordion group; open its ancestors.
    if not link.first.is_visible():
        log("Menu item hidden — expanding its parent group(s)")
        page.evaluate(
            """(idx) => {
                const a = document.querySelector('a.J_menuItem[data-index="' + idx + '"]');
                if (!a) return;
                let ul = a.closest('ul');
                while (ul) {
                    ul.classList.add('in');
                    const opener = ul.previousElementSibling;
                    if (opener && opener.hasAttribute('aria-expanded')) {
                        opener.setAttribute('aria-expanded', 'true');
                    }
                    ul = ul.parentElement ? ul.parentElement.closest('ul') : null;
                }
            }""",
            index,
        )

    link.first.click()
    log(f"Clicked a.J_menuItem[data-index='{index}']")

    frame_sel = f'iframe[name="iframe{index}"]'
    page.wait_for_selector(frame_sel, timeout=20_000)
    log(f"Frame mounted: {frame_sel}")

    frame = page.frame_locator(frame_sel)
    # Opened frames are hidden, never destroyed, so confirm this one is live by
    # waiting on content inside it rather than on a page navigation.
    frame.locator(".el-table__header-wrapper").first.wait_for(state="attached", timeout=25_000)
    log("Grid present inside frame")
    return frame


# -----------------------------------------------------------------------------
# Step 4 — prepare the grid
# -----------------------------------------------------------------------------

def reported_total(frame: FrameLocator) -> Optional[int]:
    """Read '.el-pagination__total' — the grid's own authoritative row count."""
    loc = frame.locator(".el-pagination__total").first
    try:
        text = loc.text_content(timeout=8_000) or ""
    except PWTimeout:
        return None
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def select_pending_tab(frame: FrameLocator) -> None:
    tab = frame.locator("#tab-1")
    if tab.count():
        tab.click()
        log("Activated #tab-1 (Import Confirm Pending)")
    else:
        log("WARNING: #tab-1 not found — tab ids changed?")


def set_page_size(frame: FrameLocator, size: int = 500) -> bool:
    """Switch the pager to its largest page so extraction is a single read.

    Returns True if the option was found and clicked.
    """
    sizes = frame.locator(".el-pagination__sizes")
    if sizes.count() == 0:
        log("No page-size control — grid is not paginated")
        return False

    sizes.locator(".el-input__inner").first.click()
    option = frame.locator(".el-pagination__sizes .el-select-dropdown__item",
                           has_text=f"{size}/page")
    if option.count() == 0:
        log(f"No '{size}/page' option offered; leaving page size unchanged")
        frame.locator("body").click()
        return False

    option.first.click()
    log(f"Page size set to {size}/page")
    frame.locator(".el-table__body-wrapper tr.el-table__row").first.wait_for(timeout=10_000)
    return True


# -----------------------------------------------------------------------------
# Step 5 — extract
# -----------------------------------------------------------------------------

EXTRACT_JS = """
() => {
  const root = document.querySelector('.el-table');
  if (!root) return { error: 'no .el-table found' };

  // Header: the MAIN header wrapper only. Skip the selection column and the
  // trailing gutter th, then take the label span's text -- the header cell also
  // contains the filter widget, whose option list would otherwise be swept up.
  const headEls = Array.from(
    root.querySelectorAll('.el-table__header-wrapper thead tr:first-child th')
  );

  const headers = [];
  const keptIdx = [];
  headEls.forEach((th, i) => {
    if (th.classList.contains('gutter')) return;
    if (th.classList.contains('el-table-column--selection')) { headers.push(null); keptIdx.push(i); return; }
    const cell = th.querySelector('.cell');
    let label = '';
    if (cell) {
      const span = cell.querySelector(':scope > span');
      label = (span ? span.textContent : cell.textContent) || '';
    }
    label = label.replace(/\\s+/g, ' ').trim();
    headers.push(label);
    keptIdx.push(i);
  });

  // Rows: MAIN body wrapper only. The .el-table__fixed clone holds a second
  // copy of every row whose data cells are is-hidden.
  const trs = Array.from(
    root.querySelectorAll('.el-table__body-wrapper tbody tr.el-table__row')
  );

  const rows = trs.map(tr => {
    const tds = Array.from(tr.querySelectorAll('td.el-table__cell'));
    const out = {};
    headers.forEach((label, i) => {
      if (!label) return;                     // selection column
      const td = tds[keptIdx[i]];
      if (!td) return;
      const cell = td.querySelector('.cell');
      out[label] = ((cell ? cell.innerText : td.innerText) || '').replace(/\\s+/g, ' ').trim();
    });
    return out;
  });

  return {
    headers: headers.filter(Boolean),
    rows: rows,
    domRowCount: root.querySelectorAll('tr.el-table__row').length,
    bodyRowCount: trs.length
  };
}
"""


def extract_rows(frame: FrameLocator) -> List[Dict[str, str]]:
    log_section("STEP 4 — Extract rows from the grid")

    frame.locator(".el-table__body-wrapper tr.el-table__row").first.wait_for(timeout=20_000)
    result = frame.locator(".el-table").first.evaluate(EXTRACT_JS)

    if result.get("error"):
        raise RuntimeError(result["error"])

    headers = result["headers"]
    rows = result["rows"]
    log(f"Headers ({len(headers)}): {', '.join(headers)}")
    log(f"Rows in DOM: {result['domRowCount']}  |  rows in body wrapper: {result['bodyRowCount']}")

    if result["domRowCount"] == 2 * result["bodyRowCount"]:
        log("  (the 2x DOM count is the .el-table__fixed clone — correctly excluded)")

    total = reported_total(frame)
    if total is not None:
        log(f"Grid reports Total {total}")
        if total != len(rows):
            log(f"WARNING: scraped {len(rows)} rows but the grid reports {total}. "
                f"Pagination may still be limiting the view.")

    return rows


def map_rows(raw_rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    log_section("STEP 5 — Map header labels to DB columns")

    unmapped = set()
    mapped: List[Dict[str, Any]] = []

    for raw in raw_rows:
        row: Dict[str, Any] = {}
        for header, value in raw.items():
            key = HEADER_TO_DB.get(header.strip().lower())
            if key is None:
                unmapped.add(header)
                continue
            value = (value or "").strip()
            if value and value.lower() not in ("nan", "none", "-"):
                row[key] = value
        if row.get("mawb"):
            mapped.append(row)

    if unmapped:
        log(f"Unmapped headers (ignored): {', '.join(sorted(unmapped))}")
    log(f"Mapped {len(mapped)} rows with a valid MAWB "
        f"(dropped {len(raw_rows) - len(mapped)} without one)")
    return mapped


# -----------------------------------------------------------------------------
# Step 6 — ingest
# -----------------------------------------------------------------------------

def post_bulk(target: Target, rows: List[Dict[str, Any]], token: str) -> Dict[str, Any]:
    log_section("STEP 6 — POST rows to /api/import-confirm/bulk")
    url = f"{target.base}/api/import-confirm/bulk"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    log(f"POST {url}  ({len(rows)} rows)")
    t0 = time.monotonic()
    resp = requests.post(url, json=rows, headers=headers, timeout=60)
    elapsed = time.monotonic() - t0
    resp.raise_for_status()
    data = resp.json()
    log(f"Response ({elapsed:.2f}s): upserted={data.get('upserted')}  "
        f"skipped={data.get('skipped')}  errors={len(data.get('errors', []))}")
    for err in (data.get("errors") or [])[:5]:
        log(f"  ! {err}")
    return data


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apex X-Control scraper")
    p.add_argument("--target", choices=sorted(TARGETS), default="mock",
                   help="which stack to drive (default: mock)")
    p.add_argument("--page-size", type=int, default=500,
                   help="pager size to request before extracting (default: 500)")
    p.add_argument("--no-ingest", action="store_true",
                   help="scrape and report, but do not POST to the backend")
    p.add_argument("--headed", action="store_true", help="show the browser")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    target = TARGETS[args.target]
    headless = HEADLESS and not args.headed

    username = os.environ.get("XCONTROL_USER", "")
    password = os.environ.get("XCONTROL_PASS", "")

    log_section("Apex Workflow X-Control Bot — starting")
    log(f"Target:   {target.name}  ({target.base})")
    log(f"Username: {username or '(not set — check .env)'}")
    log(f"Headless: {headless}")

    if not username or not password:
        log("ERROR: XCONTROL_USER and XCONTROL_PASS must be set in .env")
        sys.exit(1)

    token = api_login(target, username, password)

    raw_rows: List[Dict[str, str]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=60 if not headless else 0)
        context = browser.new_context(viewport={"width": 1600, "height": 950}, locale="en-US")
        page = context.new_page()
        page.on("console", lambda m: log(f"  [browser:{m.type}] {m.text}") if m.type == "error" else None)

        try:
            browser_login(page, target, username, password)
            frame = open_module(page, MENU_IMPORT_CONFIRM, "Import Confirm")
            select_pending_tab(frame)
            set_page_size(frame, args.page_size)
            raw_rows = extract_rows(frame)
        finally:
            context.close()
            browser.close()

    db_rows = map_rows(raw_rows)

    if args.no_ingest:
        log_section("Done (--no-ingest)")
        log(f"Scraped {len(raw_rows)} rows, {len(db_rows)} with a MAWB. Nothing posted.")
        for r in db_rows[:3]:
            log(f"  sample: {r}")
        return

    if not db_rows:
        log_section("Done")
        log("Nothing to ingest — no rows carried a MAWB.")
        return

    result = post_bulk(target, db_rows, token)

    log_section("Done")
    log(f"Total scraped : {len(raw_rows)}")
    log(f"Total mapped  : {len(db_rows)}")
    log(f"Upserted      : {result.get('upserted')}")
    log(f"Skipped       : {result.get('skipped')}")


if __name__ == "__main__":
    main()
