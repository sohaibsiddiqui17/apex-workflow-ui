# Apex Workflow X-Control — Mock Backend

Safe FastAPI + SQLite backend for RPA bot testing.  
The bot reads shipment data, tracks carriers, and writes ATD/ATA results back.

---

## Quick start

```bash
cd mock_server
pip install -r requirements.txt
playwright install chromium       # only needed for the bot
uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

Interactive docs: http://localhost:8090/docs  
Login page served at: http://localhost:8090/login.html  
Main app served at: http://localhost:8090/index.html

---

## Environment variables

Create `mock_server/.env` (or `apex-workflow-ui/.env`):

```
XCONTROL_USER=your_username
XCONTROL_PASS=your_password
XCONTROL_URL=http://localhost:8090   # optional, default
HEADLESS=true                        # set false to watch the browser
```

---

## End-to-end run (server + bot)

**Terminal 1 — start the server**

```bash
cd mock_server
uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

**Terminal 2 — run the bot**

```bash
cd mock_server
python xcontrol_bot.py
```

The bot will:
1. Call `POST /api/login` to verify credentials
2. Open Chromium, navigate to `http://localhost:8090/login.html`
3. Fill in credentials and click Login
4. Navigate to the main app, open Import Confirm → Pending
5. Extract all rows (all pages) from the table
6. Map JS field names to DB column names
7. POST all rows to `POST /api/import-confirm/bulk`
8. Print a timestamped log of every step

---

## Database

Auto-created as `mock_server/apex_mock.db` on first run.  
Two tables: `import_confirm` and `pickup_report`.

---

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check + row counts |
| GET | `/login.html` | Serve frontend login page |
| GET | `/index.html` | Serve frontend main app |
| POST | `/api/login` | Credential check — returns `{token, success}` |
| POST | `/api/upload/import-confirm` | Upload `.xlsx` / `.csv` — upserts on MAWB |
| POST | `/api/upload/pickup-report` | Upload `.xlsx` / `.csv` — upserts on BL No |
| GET | `/api/import-confirm` | List rows (filters: status, airline, firm_code, bot_status; pagination) |
| GET | `/api/import-confirm/{mawb}` | Single MAWB detail |
| PATCH | `/api/import-confirm/{mawb}` | **Bot writes back** ATA/ATD/bot_status for one MAWB |
| POST | `/api/import-confirm/batch-update` | **Bot writes back** results for many MAWBs at once |
| POST | `/api/import-confirm/bulk` | **Bot ingest** — bulk upsert scraped rows (JSON array) |
| GET | `/api/pickup-report` | List rows (filter: shipment_status; pagination) |
| GET | `/api/stats` | Dashboard counts — by status, bot_status, airline, firm_code |
| POST | `/api/reset` | Delete all rows (test utility) |

---

## Upload format

The Excel/CSV column headers are mapped automatically (case-insensitive, extra spaces stripped).  
Supported aliases are defined in `IC_COL_MAP` / `PR_COL_MAP` in `main.py`.

**Minimum required column for Import Confirm:** `M#` or `MAWB`  
**Minimum required column for Pickup Report:** `BL No` or `B/L`

---

## Example curl calls

### Login

```bash
curl -X POST http://localhost:8090/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secret"}'
```

### Upload Import Confirm sheet

```bash
curl -X POST http://localhost:8090/api/upload/import-confirm \
  -F "file=@import_confirm.xlsx"
```

### Bulk ingest (bot)

```bash
curl -X POST http://localhost:8090/api/import-confirm/bulk \
  -H "Content-Type: application/json" \
  -d '[{"mawb":"123-45678901","status":"New","airline":"UA","eta":"2024-07-15"}]'
```

### Bot single writeback

```bash
curl -X PATCH http://localhost:8090/api/import-confirm/123-45678901 \
  -H "Content-Type: application/json" \
  -d '{
    "ata": "2024-07-15T08:30:00Z",
    "bot_status": "arrived",
    "carrier_scrape": "UA",
    "cross_check_flag": "match"
  }'
```

### Bot batch writeback

```bash
curl -X POST http://localhost:8090/api/import-confirm/batch-update \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"mawb":"123-45678901","result":{"ata":"2024-07-15T08:30:00Z","bot_status":"arrived"}},
      {"mawb":"234-56789012","result":{"bot_status":"no_eta"}}
    ]
  }'
```

### Dashboard stats

```bash
curl http://localhost:8090/api/stats
```

### Reset all data

```bash
curl -X POST http://localhost:8090/api/reset
```

---

## Wiring the RPA bot

Point your bot at `http://localhost:8090` (or your server IP on port 8090).

| Step | What the bot does | API call |
|------|------------------|----------|
| 1 | Validate credentials | `POST /api/login` |
| 2 | Scrape Import Confirm table | Playwright → `index.html` |
| 3 | Push scraped rows | `POST /api/import-confirm/bulk` |
| 4 | Carrier lookup loop | external |
| 5 | Write back ATA/ATD per MAWB | `PATCH /api/import-confirm/{mawb}` |
| 6 | Flush batch results | `POST /api/import-confirm/batch-update` |
| 7 | Monitor progress | `GET /api/stats` |

---

## Frontend integration

The frontend is **not** a single page. `index.html` is only the HPlus shell; every
module lives in its own iframe under `frames/`. See the root `README.md` for the
four-layer map and the scraping hazards it reproduces.

The server serves all of it:

- Login page: `http://localhost:8090/login.html`  (`/` redirects here)
- Shell:      `http://localhost:8090/index.html`
- Frames:     `http://localhost:8090/frames/importConfirm.html` etc.
- Assets:     `http://localhost:8090/assets/el-table.js` etc.

The backend base URL lives in `assets/api.js`. Override it per session with a
query string instead of editing the file:

```
http://localhost:8090/login.html?api=http://192.168.1.50:8090
```

When the page is served from port 8090 it defaults to its own origin.

---

## Bot and tests

```bash
python xcontrol_bot.py                        # scrape the mock, POST to /bulk
python xcontrol_bot.py --no-ingest --headed   # watch it, post nothing
python xcontrol_bot.py --target production --no-ingest

python smoke_test.py                          # 37 structural assertions
```

`xcontrol_bot.py` drives the mock and the real portal with the same code path:
menu click -> `frame_locator('iframe[name="iframe16"]')` -> page size 500 ->
extract by header text from `.el-table__body-wrapper` -> map to DB columns.
`--target production` only swaps the base URL and login path.
