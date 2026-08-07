# Apex Workflow X-Control — Mock Backend

Safe FastAPI + SQLite backend for RPA bot testing.  
The bot reads shipment data, tracks carriers, and writes ATD/ATA results back.

---

## Quick start

```bash
cd mock_server
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

Interactive docs: http://localhost:8090/docs

---

## Database

Auto-created as `mock_server/apex_mock.db` on first run.  
Two tables: `import_confirm` and `pickup_report`.

---

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check + row counts |
| POST | `/api/upload/import-confirm` | Upload `.xlsx` / `.csv` — upserts on MAWB |
| POST | `/api/upload/pickup-report` | Upload `.xlsx` / `.csv` — upserts on BL No |
| GET | `/api/import-confirm` | List rows (filters: status, airline, firm_code, bot_status; pagination) |
| GET | `/api/import-confirm/{mawb}` | Single MAWB detail |
| PATCH | `/api/import-confirm/{mawb}` | **Bot writes back** ATA/ATD/bot_status for one MAWB |
| POST | `/api/import-confirm/batch-update` | **Bot writes back** results for many MAWBs at once |
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

### Upload Import Confirm sheet

```bash
curl -X POST http://localhost:8090/api/upload/import-confirm \
  -F "file=@import_confirm.xlsx"
```

### Upload Pickup Report sheet

```bash
curl -X POST http://localhost:8090/api/upload/pickup-report \
  -F "file=@pickup_report.xlsx"
```

### Bot writes back ATA/ATD for a single MAWB

```bash
curl -X PATCH http://localhost:8090/api/import-confirm/123-45678901 \
  -H "Content-Type: application/json" \
  -d '{
    "ata": "2024-07-15T08:30:00Z",
    "atd": "2024-07-15T10:00:00Z",
    "source_ata": "CarrierPortal",
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
      {
        "mawb": "123-45678901",
        "result": { "ata": "2024-07-15T08:30:00Z", "bot_status": "arrived" }
      },
      {
        "mawb": "234-56789012",
        "result": { "bot_status": "no_eta" }
      }
    ]
  }'
```

### Get stats for dashboard

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

1. **Seed data** — upload the daily Excel export via the frontend Upload button or curl.
2. **Read rows** — `GET /api/import-confirm?bot_status=pending&page_size=200` to get the work queue.
3. **Write results** — `PATCH /api/import-confirm/{mawb}` after each carrier lookup.
4. **Batch write** — `POST /api/import-confirm/batch-update` to flush results in bulk.
5. **Monitor** — `GET /api/stats` to see overall bot_status breakdown.

---

## Frontend integration

The frontend (`index.html`) connects to `http://localhost:8090` by default.  
Change `API_BASE` at the top of the `<script>` section in `index.html` to point at a remote server.
