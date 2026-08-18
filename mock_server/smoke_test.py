"""
Structural smoke test for the mock X-Control stack.

Asserts the properties that make the mock a faithful stand-in for production:
frame depth and persistence, Element UI class structure, the fixed-column row
clone, the is-hidden inversion on the selection column, and header/enum
fidelity. Run it after any change to the frames or to assets/el-table.js.

  cd mock_server
  python smoke_test.py                     # against http://localhost:8090
  python smoke_test.py --headed
"""

from __future__ import annotations

import argparse
import os
import sys

from playwright.sync_api import sync_playwright

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

BASE = os.environ.get("XCONTROL_URL", "http://localhost:8090")
USER = os.environ.get("XCONTROL_USER", "botuser")
PASS = os.environ.get("XCONTROL_PASS", "botpass")

_passed = 0
_failed = 0


def check(label: str, actual, expected=None, predicate=None) -> None:
    global _passed, _failed
    if predicate is not None:
        ok = predicate(actual)
        detail = f"{actual!r}"
    else:
        ok = actual == expected
        detail = f"{actual!r} == {expected!r}"
    if ok:
        _passed += 1
        print(f"  PASS  {label}  ({detail})")
    else:
        _failed += 1
        print(f"  FAIL  {label}  (got {actual!r}, expected {expected!r})")


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        page = browser.new_context(viewport={"width": 1600, "height": 950}).new_page()

        # ---------------------------------------------------------- layer 1
        section("Layer 1 - login page")
        page.goto(f"{BASE}/login.html", wait_until="domcontentloaded")
        check("#login is a button, not a submit",
              page.get_attribute("#login", "type"), "button")
        check("hidden SSO frames mounted",
              page.locator("iframe[data-sso]").count(), predicate=lambda n: n >= 40)
        check("authUrlList populated",
              page.evaluate("() => (window.authUrlList || []).length"),
              predicate=lambda n: n >= 40)

        page.fill("#username", USER)
        page.fill("#password", PASS)
        page.click("#login")
        page.wait_for_selector("#side-menu", timeout=30_000)

        # ---------------------------------------------------------- layer 2
        section("Layer 2 - HPlus shell")
        check("menu items carry data-index",
              page.locator("a.J_menuItem[data-index]").count(), 59)
        check("Import Confirm is index 16",
              page.locator('a.J_menuItem[data-index="16"]').count(), 1)
        check("home frame mounted as iframe0",
              page.locator('iframe.J_iframe[name="iframe0"]').count(), 1)
        check("one tab chip to start",
              page.locator("a.J_menuTab").count(), 1)

        # ---------------------------------------------------------- layer 3
        section("Layer 3 - iframe routing")
        page.evaluate("() => window.__APEX_SHELL__.openMenu(16, 'Import Confirm')")
        page.wait_for_selector('iframe[name="iframe16"]', timeout=20_000)
        check("importConfirm frame mounted",
              page.locator('iframe[name="iframe16"]').count(), 1)
        check("home frame still mounted (hidden, not destroyed)",
              page.locator('iframe[name="iframe0"]').count(), 1)
        check("home frame is hidden",
              page.eval_on_selector('iframe[name="iframe0"]',
                                    "el => el.style.display"), "none")

        page.evaluate("() => window.__APEX_SHELL__.openMenu(2, 'Update ATD&ATA')")
        page.wait_for_selector('iframe[name="iframe2"]', timeout=20_000)
        check("three frames now mounted simultaneously",
              page.locator("iframe.J_iframe").count(), 3)
        check("tab chips track open frames",
              page.locator("a.J_menuTab").count(), 3)

        page.evaluate("() => window.__APEX_SHELL__.showFrame(16)")

        # ---------------------------------------------------------- layer 4
        section("Layer 4 - Element UI grid")
        ic = page.frame_locator('iframe[name="iframe16"]')
        ic.locator(".el-table__body-wrapper tr.el-table__row").first.wait_for(timeout=20_000)

        stats = ic.locator(".el-table").first.evaluate("""
          (root) => {
            const q = s => root.querySelectorAll(s).length;
            const mainSel = root.querySelector(
              '.el-table__body-wrapper td.el-table-column--selection');
            const fixSel = root.querySelector(
              '.el-table__fixed td.el-table-column--selection');
            const mainData = root.querySelector(
              '.el-table__body-wrapper tr.el-table__row td.el-table_1_column_2');
            const fixData = root.querySelector(
              '.el-table__fixed tr.el-table__row td.el-table_1_column_2');
            return {
              allRows:   q('tr.el-table__row'),
              bodyRows:  q('.el-table__body-wrapper tr.el-table__row'),
              fixedRows: q('.el-table__fixed tr.el-table__row'),
              headerWrappers: q('.el-table__header-wrapper'),
              fixedHeaderWrappers: q('.el-table__fixed-header-wrapper'),
              headerCells: q('.el-table__header-wrapper thead th'),
              gutter: q('.el-table__header-wrapper thead th.gutter'),
              cellDivs: q('.el-table__body-wrapper td.el-table__cell > div.cell'),
              links: q('.el-table__body-wrapper a.apex_link_mini'),
              filterInputs: q('input[placeholder="filter column"]'),
              dateInputs: q('input[placeholder="Start date"]'),
              dropdownItems: q('.el-select-dropdown__item'),
              mainSelHidden: mainSel ? mainSel.classList.contains('is-hidden') : null,
              fixedSelHidden: fixSel ? fixSel.classList.contains('is-hidden') : null,
              mainDataHidden: mainData ? mainData.classList.contains('is-hidden') : null,
              fixedDataHidden: fixData ? fixData.classList.contains('is-hidden') : null
            };
          }
        """)

        check("body-wrapper rows", stats["bodyRows"], 25)
        check("fixed clone duplicates every row", stats["fixedRows"], 25)
        check("unscoped query sees 2x rows (the production hazard)",
              stats["allRows"], 50)
        check("split header/body tables", stats["headerWrappers"], 1)
        check("fixed clone has its own header", stats["fixedHeaderWrappers"], 1)
        check("29 header cells + gutter", stats["headerCells"], 30)
        check("trailing gutter th present", stats["gutter"], 1)
        check("every td wraps content in div.cell",
              stats["cellDivs"], 25 * 29)
        check("M# rendered as el-link", stats["links"], 25)
        check("per-column filter inputs",
              stats["filterInputs"], predicate=lambda n: n >= 15)
        check("date-range filters",
              stats["dateInputs"], predicate=lambda n: n >= 5)
        check("dropdown option lists inlined",
              stats["dropdownItems"], predicate=lambda n: n > 1500)

        section("Layer 4 - is-hidden inversion")
        check("selection column hidden in main table", stats["mainSelHidden"], True)
        check("selection column visible in fixed clone", stats["fixedSelHidden"], False)
        check("data column visible in main table", stats["mainDataHidden"], False)
        check("data column hidden in fixed clone", stats["fixedDataHidden"], True)

        section("Layer 4 - tabs and pagination")
        check("three el-tabs panes", ic.locator(".el-tabs__item").count(), 3)
        check("#tab-1 active by default",
              ic.locator("#tab-1").get_attribute("aria-selected"), "true")
        check("pagination reports total",
              (ic.locator(".el-pagination__total").first.text_content() or "").strip(),
              "Total 25")

        section("Layer 4 - row selection through the fixed clone")
        # The native input is visually hidden (0x0, opacity 0) exactly as in
        # Element UI; the clickable target is .el-checkbox__inner inside the
        # wrapping <label>. This is the selector a bot must use in production.
        ic.locator(
            '.el-table__fixed tbody tr.el-table__row'
        ).first.locator('.el-checkbox__inner').first.click()
        synced = ic.locator(".el-table").first.evaluate("""
          (root) => root.querySelectorAll(
            '.el-checkbox__original[data-row-index="0"]:checked').length
        """)
        check("clicking the visible clone checkbox syncs both copies", synced, 2)
        check("selection banner reflects the click",
              (ic.locator("#ic-selection-count").text_content() or "").strip(), "1")

        # ------------------------------------------------------- ATD / ATA
        section("Update ATD & ATA frame")
        page.evaluate("() => window.__APEX_SHELL__.showFrame(2)")
        atd = page.frame_locator('iframe[name="iframe2"]')
        atd.locator(".el-table__body-wrapper tr.el-table__row").first.wait_for(timeout=20_000)
        check("ATD rows", atd.locator(".el-table__body-wrapper tr.el-table__row").count(), 10)
        check("ATD fixed clone present",
              atd.locator(".el-table__fixed tr.el-table__row").count(), 10)
        check("ATD toolbar actions",
              atd.locator("button[data-action]").count(), predicate=lambda n: n >= 6)
        check("Update ATD button present",
              atd.locator('button[data-action="update-atd"]').count(), 1)

        browser.close()

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
