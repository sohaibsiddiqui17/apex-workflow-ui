# apex-workflow-ui

A structurally faithful mock of the Apex Workflow **X-Control** portal, built as a
safe target for the RPA bot that scrapes Import Confirm and writes ATD/ATA back.

The point of this repo is not to look like X-Control — it is to **be shaped like
it**, so that a selector written against the mock also works against production.

---

## The four layers

Production nests the actual grid three levels below the URL you log into. The
mock reproduces that exactly:

| Layer | Production | Mock |
|-------|-----------|------|
| 1 · Login | `www.apexworkflow.com/login` — `<button type="button" id="login">`, then ~100 hidden cross-domain SSO iframes | `login.html` + `frames/sso.html` |
| 2 · Shell | HPlus / AdminLTE jQuery frame, `ul#side-menu` with 59 `a.J_menuItem[data-index]`, tab strip of `a.J_menuTab[data-id]` | `index.html` + `assets/hplus.css` |
| 3 · Frame | one `iframe[name="iframe{data-index}"]` per open tab, hidden with `display:none` rather than destroyed | same |
| 4 · Grid | Vue 2 + Element UI — `el-table`, `el-tabs`, `el-dialog`, `data-v-*` scoped styles | `frames/*.html` + `assets/el-table.js` |

```
login.html
  └─ index.html                        (the shell — not the app)
       ├─ iframe[name="iframe0"]   →  frames/home.html
       ├─ iframe[name="iframe16"]  →  frames/importConfirm.html
       ├─ iframe[name="iframe2"]   →  frames/updateAtdAta.html
       └─ iframe[name="iframeN"]   →  frames/placeholder.html   (the other 56 menu entries)
```

**There is no Shadow DOM anywhere**, because production has none. X-Control's
encapsulation is the iframe boundary plus Vue's `data-v-*` scoping, and that is
what the mock reproduces. Reaching into a frame requires
`page.frame_locator('iframe[name="iframe16"]')` — not `page.evaluate`.

---

## Details that will break a naive scraper

These are reproduced deliberately. They are the reason the mock exists.

**1. Every row is rendered twice.** Element UI clones the whole table into
`.el-table__fixed` to implement the frozen checkbox column. An unscoped
`querySelectorAll('tr.el-table__row')` returns **50** rows for 25 records.

```js
document.querySelectorAll('tr.el-table__row')                       // 50 — wrong
document.querySelectorAll('.el-table__body-wrapper tr.el-table__row') // 25 — right
```

**2. The selection column is inverted between the copies.** In the main table
the checkbox column is `is-hidden`; in the fixed clone the *data* columns are.
So: **read data from `.el-table__body-wrapper`, click checkboxes in
`.el-table__fixed`.** And click `.el-checkbox__inner`, not
`.el-checkbox__original` — the native input is a 0×0 transparent element.

**3. Column classes are positional.** `el-table_1_column_8` is M# only until
someone inserts a column. Build a header-text → index map instead.

**4. Header cells contain their own filter widget.** Reading `th.innerText`
sweeps up the entire dropdown option list. Read the label span:
`th .cell > span`.

**5. Frames are never unmounted.** Opening a second tab hides the first frame,
it does not navigate. Waiting for a page load after clicking a menu item hangs.

---

## Layout

```
index.html                 the HPlus shell
login.html                 SSO login + hidden SSO frame fan-out
frames/
  home.html                dashboard, upload controls, quick access
  importConfirm.html       3 el-tabs, 28-column el-table, 12 toolbar actions, 6 dialogs
  updateAtdAta.html        ATD/ATA grid, single + batch update, time-rule suggestions
  placeholder.html         stub for unmodelled menu entries
  sso.html                 per-domain SSO token sink
assets/
  hplus.css                shell theme (Bootstrap 3 / AdminLTE subset)
  element-mock.css         Element UI 2.x subset — real class names
  el-table.js              renders Element UI's exact table DOM, clone included
  apex-enums.js            controlled vocabularies, extracted from the capture
  apex-data.js             row fixtures + column models
  apex-menu.js             the 59-item menu tree, extracted from the capture
  api.js                   backend base URL + row mapping
mock_server/
  main.py                  FastAPI + SQLite, 13 endpoints
  xcontrol_bot.py          Playwright driver (works against mock and production)
  smoke_test.py            37 structural assertions
```

`assets/apex-enums.js` and `assets/apex-menu.js` are **generated** from the saved
production pages in `../New DOM Structure`. Regenerate them from a fresh capture
rather than editing by hand. Between them they carry the real 516-airline list,
114 offices, the 34-tag vocabulary and all 59 menu indices.

---

## Running it

```bash
cd mock_server
pip install -r requirements.txt
playwright install chromium

cat > .env <<'EOF'
XCONTROL_USER=botuser
XCONTROL_PASS=botpass
XCONTROL_URL=http://localhost:8090
HEADLESS=true
EOF

uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

- Login: <http://localhost:8090/login.html> (`/` redirects here)
- Shell: <http://localhost:8090/index.html>
- API docs: <http://localhost:8090/docs>

Point the frontend at a different backend with `?api=` — e.g.
`login.html?api=http://localhost:8090`. It is remembered for the session.

### The bot

One driver handles both targets, because the DOM shapes now match:

```bash
python xcontrol_bot.py                              # scrape mock → POST /bulk
python xcontrol_bot.py --no-ingest                  # scrape and print only
python xcontrol_bot.py --headed                     # watch it
python xcontrol_bot.py --target production --no-ingest
```

It logs in, clicks `a.J_menuItem[data-index="16"]`, enters
`iframe[name="iframe16"]`, sets the pager to 500/page, extracts by header text
from the body wrapper, cross-checks the count against `.el-pagination__total`,
and maps headers onto DB columns.

### Structural tests

```bash
python smoke_test.py
```

37 assertions across all four layers: frame depth and persistence, the row
clone, the `is-hidden` inversion, header/gutter counts, `div.cell` wrapping,
checkbox sync, tabs and pagination. Run it after touching any frame or
`assets/el-table.js`.

---

## Known gaps

- **`frames/updateAtdAta.html` is unverified.** The production capture contains
  only that page's `<iframe>` tag, never its body. Its column set and dialogs are
  modelled on the Import Confirm grid and the earlier flat mock. Save the real
  page with its sidecar folder to close this.
- **The `Confirm` action is local.** The success-type `Confirm` button is the
  terminal step of the Import Confirm workflow; it updates the grid but has no
  modelled API endpoint.
