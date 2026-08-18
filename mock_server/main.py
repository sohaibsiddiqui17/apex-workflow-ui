"""
Apex Workflow X-Control — Mock Backend
Safe test environment for the RPA bot that reads shipment data,
tracks carriers, and writes ATD/ATA results back.

Run: uvicorn main:app --host 0.0.0.0 --port 8090 --reload
"""

from __future__ import annotations

import base64
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────
# App & CORS
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Apex Workflow X-Control Mock API",
    description="Mock backend for RPA bot testing — Import Confirm & Pickup Report",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Frontend static serving  (login.html / index.html live in the parent dir)
# ─────────────────────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@app.get("/login.html", include_in_schema=False)
def frontend_login():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))


@app.get("/index.html", include_in_schema=False)
@app.get("/app", include_in_schema=False)
def frontend_app():
    """The HPlus admin shell. It hosts every module in its own iframe, the way
    the real portal does, so this is only layer 2 of 4."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/", include_in_schema=False)
def frontend_root():
    return RedirectResponse(url="/login.html")


# Shared stylesheets, fixtures and the el-table renderer.
_assets_dir = os.path.join(FRONTEND_DIR, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

# Iframe payloads: home.html, importConfirm.html, updateAtdAta.html,
# placeholder.html, sso.html. The shell loads these by relative path, so they
# must be reachable at /frames/<name> for the served build to behave like the
# file:// build.
_frames_dir = os.path.join(FRONTEND_DIR, "frames")
if os.path.isdir(_frames_dir):
    app.mount("/frames", StaticFiles(directory=_frames_dir), name="frames")

# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────

# On Railway a persistent volume is mounted at /data.
# Locally we keep the DB next to main.py.
_data_dir = "/data" if os.path.isdir("/data") else os.path.dirname(__file__)
DB_PATH = os.path.join(_data_dir, "apex_mock.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS import_confirm (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                mawb                TEXT    UNIQUE NOT NULL,
                status              TEXT,
                tags                TEXT,
                op_remarks          TEXT,
                abi_query_status    TEXT,
                abi_query_match     TEXT,
                uld_no              TEXT,
                hawb_customer       TEXT,
                hawb                TEXT,
                eta                 TEXT,
                pol                 TEXT,
                pod                 TEXT,
                airline             TEXT,
                firm_code           TEXT,
                flight_no           TEXT,
                dest_handling_office TEXT,
                dest_gateway_office TEXT,
                address             TEXT,
                last_free_date      TEXT,
                wt                  TEXT,
                sc_job_status       TEXT,
                sc_job_no           TEXT,
                pre_alert_date      TEXT,
                dest_cs             TEXT,
                is_ovs_agent        TEXT,
                query_send_date     TEXT,
                query_update_date   TEXT,
                operator            TEXT,
                -- Bot result columns (written back by RPA bot)
                ata                 TEXT,
                atd                 TEXT,
                source_ata          TEXT,
                source_atd          TEXT,
                bot_eta             TEXT,
                bot_etd             TEXT,
                bot_status          TEXT    DEFAULT 'pending',
                carrier_scrape      TEXT,
                cross_check_flag    TEXT,
                last_updated        TEXT
            );

            CREATE TABLE IF NOT EXISTS pickup_report (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                bl_no           TEXT    UNIQUE NOT NULL,
                shipper         TEXT,
                equip_id        TEXT,
                lading_point    TEXT,
                owner           TEXT,
                final_dest      TEXT,
                pickup_scac     TEXT,
                tl_scac         TEXT,
                pou_actual      TEXT,
                cue_actual      TEXT,
                cur_actual      TEXT,
                tnf_actual      TEXT,
                cat_actual      TEXT,
                paa_actual      TEXT,
                doa_actual      TEXT,
                air_dwell       TEXT,
                shipment_status TEXT,
                pud_actual      TEXT,
                total_cartons   TEXT,
                total_units     TEXT,
                notes           TEXT
            );
        """)


init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Column name normalisation maps  (Excel header → DB column)
# ─────────────────────────────────────────────────────────────────────────────

IC_COL_MAP: Dict[str, str] = {
    # Status / tags
    "status": "status",
    "tags": "tags",
    "op remarks": "op_remarks",
    "op_remarks": "op_remarks",
    "opremarks": "op_remarks",
    # ABI
    "abi query status": "abi_query_status",
    "abi_query_status": "abi_query_status",
    "abistatus": "abi_query_status",
    "abi query match": "abi_query_match",
    "abi_query_match": "abi_query_match",
    "abimatch": "abi_query_match",
    # ULD / HAWB / MAWB
    "uld#": "uld_no",
    "uld no": "uld_no",
    "uld_no": "uld_no",
    "uld": "uld_no",
    "hawb customer / account code / cid / gid": "hawb_customer",
    "hawb customer": "hawb_customer",
    "hawb_customer": "hawb_customer",
    "customer": "hawb_customer",
    "account code": "hawb_customer",
    "m#": "mawb",
    "mawb": "mawb",
    "master awb": "mawb",
    "master_awb": "mawb",
    "h#": "hawb",
    "hawb": "hawb",
    "house awb": "hawb",
    # Dates / routing
    "eta": "eta",
    "pol": "pol",
    "pod": "pod",
    "airline": "airline",
    "firm code": "firm_code",
    "firm_code": "firm_code",
    "firmcode": "firm_code",
    "flight no": "flight_no",
    "flight_no": "flight_no",
    "flightno": "flight_no",
    "flight": "flight_no",
    "dest handling office": "dest_handling_office",
    "dest_handling_office": "dest_handling_office",
    "dest gateway office": "dest_gateway_office",
    "dest_gateway_office": "dest_gateway_office",
    "address": "address",
    "last free date": "last_free_date",
    "last_free_date": "last_free_date",
    "lfd": "last_free_date",
    "wt": "wt",
    "sc job status": "sc_job_status",
    "sc_job_status": "sc_job_status",
    "scjobstatus": "sc_job_status",
    "sc job no": "sc_job_no",
    "sc_job_no": "sc_job_no",
    "scjob": "sc_job_no",
    "pre-alert date": "pre_alert_date",
    "pre_alert_date": "pre_alert_date",
    "prealertdate": "pre_alert_date",
    "dest cs": "dest_cs",
    "dest_cs": "dest_cs",
    "is ovs agent": "is_ovs_agent",
    "is_ovs_agent": "is_ovs_agent",
    "isovsagent": "is_ovs_agent",
    "query send date": "query_send_date",
    "query_send_date": "query_send_date",
    "querysenddate": "query_send_date",
    "query update date": "query_update_date",
    "query_update_date": "query_update_date",
    "queryupdatedate": "query_update_date",
    "operator": "operator",
}

PR_COL_MAP: Dict[str, str] = {
    "bl no": "bl_no",
    "bl_no": "bl_no",
    "b/l": "bl_no",
    "b/l no": "bl_no",
    "shipper": "shipper",
    "equip id": "equip_id",
    "equip_id": "equip_id",
    "equipment id": "equip_id",
    "lading point": "lading_point",
    "lading_point": "lading_point",
    "owner": "owner",
    "final dest": "final_dest",
    "final_dest": "final_dest",
    "final destination": "final_dest",
    "pickup scac": "pickup_scac",
    "pickup_scac": "pickup_scac",
    "tl scac": "tl_scac",
    "tl_scac": "tl_scac",
    "pou actual": "pou_actual",
    "pou_actual": "pou_actual",
    "cue actual": "cue_actual",
    "cue_actual": "cue_actual",
    "cur actual": "cur_actual",
    "cur_actual": "cur_actual",
    "tnf actual": "tnf_actual",
    "tnf_actual": "tnf_actual",
    "cat actual": "cat_actual",
    "cat_actual": "cat_actual",
    "paa actual": "paa_actual",
    "paa_actual": "paa_actual",
    "doa actual": "doa_actual",
    "doa_actual": "doa_actual",
    "air dwell": "air_dwell",
    "air_dwell": "air_dwell",
    "shipment status": "shipment_status",
    "shipment_status": "shipment_status",
    "pud actual": "pud_actual",
    "pud_actual": "pud_actual",
    "total cartons": "total_cartons",
    "total_cartons": "total_cartons",
    "total units": "total_units",
    "total_units": "total_units",
    "notes": "notes",
}


def norm_header(h: str) -> str:
    return str(h).lower().strip()


def map_df_to_db(df: pd.DataFrame, col_map: Dict[str, str]) -> pd.DataFrame:
    """Rename DataFrame columns using the normalised mapping."""
    rename: Dict[str, str] = {}
    for col in df.columns:
        mapped = col_map.get(norm_header(col))
        if mapped:
            rename[col] = mapped
    df = df.rename(columns=rename)
    # Drop unmapped columns
    known = set(col_map.values())
    return df[[c for c in df.columns if c in known]]


def df_to_str(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all values to strings, replacing NaN with None."""
    return df.where(pd.notna(df), None).astype(object).where(pd.notna(df), None)


def rows_to_dicts(rows) -> List[Dict]:
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class BotResult(BaseModel):
    ata: Optional[str] = None
    atd: Optional[str] = None
    source_ata: Optional[str] = None
    source_atd: Optional[str] = None
    bot_eta: Optional[str] = None
    bot_etd: Optional[str] = None
    bot_status: Optional[str] = None   # pending | arrived | no_eta | error
    carrier_scrape: Optional[str] = None
    cross_check_flag: Optional[str] = None


class BatchItem(BaseModel):
    mawb: str
    result: BotResult


class BatchUpdate(BaseModel):
    items: List[BatchItem]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_import_confirm(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    row.setdefault("bot_status", "pending")
    row["last_updated"] = now_iso()
    cols = list(row.keys())
    placeholders = ", ".join(["?" for _ in cols])
    updates = ", ".join([f"{c}=excluded.{c}" for c in cols if c != "mawb"])
    sql = (
        f"INSERT INTO import_confirm ({', '.join(cols)}) VALUES ({placeholders})"
        f" ON CONFLICT(mawb) DO UPDATE SET {updates}"
    )
    conn.execute(sql, [row[c] for c in cols])


def _upsert_pickup_report(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    cols = list(row.keys())
    placeholders = ", ".join(["?" for _ in cols])
    updates = ", ".join([f"{c}=excluded.{c}" for c in cols if c != "bl_no"])
    sql = (
        f"INSERT INTO pickup_report ({', '.join(cols)}) VALUES ({placeholders})"
        f" ON CONFLICT(bl_no) DO UPDATE SET {updates}"
    )
    conn.execute(sql, [row[c] for c in cols])


# ─────────────────────────────────────────────────────────────────────────────
# Auth endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/login", summary="Mock login — returns a bearer token")
def login(req: LoginRequest):
    if not req.username or not req.password:
        raise HTTPException(400, "username and password are required")

    # In a real deployment check against a user table.
    # For the mock, validate against .env creds if set; otherwise accept anything.
    env_user = os.environ.get("XCONTROL_USER", "")
    env_pass = os.environ.get("XCONTROL_PASS", "")
    if env_user and env_pass:
        if req.username != env_user or req.password != env_pass:
            raise HTTPException(401, "Invalid credentials")

    # Issue a trivial mock token (not a real JWT — safe for local test use only)
    raw = f"{req.username}:{now_iso()}"
    token = base64.b64encode(raw.encode()).decode()
    return {"success": True, "token": token, "username": req.username}


# ─────────────────────────────────────────────────────────────────────────────
# Upload endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/upload/import-confirm", summary="Upload Import Confirm .xlsx")
async def upload_import_confirm(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(400, "Only .xlsx / .xls / .csv files are accepted")

    contents = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents), dtype=str)
        else:
            df = pd.read_excel(io.BytesIO(contents), dtype=str)
    except Exception as exc:
        raise HTTPException(422, f"Failed to parse file: {exc}")

    df = map_df_to_db(df, IC_COL_MAP)
    df = df_to_str(df)

    if "mawb" not in df.columns:
        raise HTTPException(422, "Could not find a MAWB / M# column in the file")

    upserted = 0
    skipped = 0
    with get_conn() as conn:
        for _, row_s in df.iterrows():
            row = {k: v for k, v in row_s.to_dict().items() if v is not None}
            mawb = row.get("mawb")
            if not mawb or str(mawb).strip() in ("", "nan", "None"):
                skipped += 1
                continue
            row["mawb"] = str(mawb).strip()
            try:
                _upsert_import_confirm(conn, row)
                upserted += 1
            except Exception:
                skipped += 1

    return {"status": "ok", "upserted": upserted, "skipped": skipped}


@app.post("/api/upload/pickup-report", summary="Upload Pickup Report .xlsx")
async def upload_pickup_report(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(400, "Only .xlsx / .xls / .csv files are accepted")

    contents = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents), dtype=str)
        else:
            df = pd.read_excel(io.BytesIO(contents), dtype=str)
    except Exception as exc:
        raise HTTPException(422, f"Failed to parse file: {exc}")

    df = map_df_to_db(df, PR_COL_MAP)
    df = df_to_str(df)

    if "bl_no" not in df.columns:
        raise HTTPException(422, "Could not find a BL No column in the file")

    upserted = 0
    skipped = 0
    with get_conn() as conn:
        for _, row_s in df.iterrows():
            row = {k: v for k, v in row_s.to_dict().items() if v is not None}
            bl_no = row.get("bl_no")
            if not bl_no or str(bl_no).strip() in ("", "nan", "None"):
                skipped += 1
                continue
            row["bl_no"] = str(bl_no).strip()
            try:
                _upsert_pickup_report(conn, row)
                upserted += 1
            except Exception:
                skipped += 1

    return {"status": "ok", "upserted": upserted, "skipped": skipped}


# ─────────────────────────────────────────────────────────────────────────────
# Import Confirm read endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/import-confirm", summary="List import confirm rows")
def list_import_confirm(
    status: Optional[str] = Query(None),
    airline: Optional[str] = Query(None),
    firm_code: Optional[str] = Query(None),
    bot_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    clauses: List[str] = []
    params: List[Any] = []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if airline:
        clauses.append("airline = ?")
        params.append(airline)
    if firm_code:
        clauses.append("firm_code = ?")
        params.append(firm_code)
    if bot_status:
        clauses.append("bot_status = ?")
        params.append(bot_status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    offset = (page - 1) * page_size

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM import_confirm {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM import_confirm {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),
        "items": rows_to_dicts(rows),
    }


@app.get("/api/import-confirm/{mawb}", summary="Get single import confirm row")
def get_import_confirm(mawb: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM import_confirm WHERE mawb = ?", [mawb]
        ).fetchone()
    if not row:
        raise HTTPException(404, f"MAWB {mawb!r} not found")
    return dict(row)


# ─────────────────────────────────────────────────────────────────────────────
# Bot write-back endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.patch("/api/import-confirm/{mawb}", summary="Bot writes back results for a single MAWB")
def patch_import_confirm(mawb: str, result: BotResult):
    updates = {k: v for k, v in result.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["last_updated"] = now_iso()

    set_clause = ", ".join([f"{k} = ?" for k in updates])
    params = list(updates.values()) + [mawb]

    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE import_confirm SET {set_clause} WHERE mawb = ?", params
        )
        if cur.rowcount == 0:
            raise HTTPException(404, f"MAWB {mawb!r} not found")

    return {"status": "ok", "mawb": mawb, "updated": list(updates.keys())}


@app.post("/api/import-confirm/batch-update", summary="Bot writes back results for multiple MAWBs")
def batch_update_import_confirm(payload: BatchUpdate):
    results = []
    with get_conn() as conn:
        for item in payload.items:
            updates = {k: v for k, v in item.result.model_dump().items() if v is not None}
            if not updates:
                results.append({"mawb": item.mawb, "status": "skipped"})
                continue
            updates["last_updated"] = now_iso()
            set_clause = ", ".join([f"{k} = ?" for k in updates])
            params = list(updates.values()) + [item.mawb]
            cur = conn.execute(
                f"UPDATE import_confirm SET {set_clause} WHERE mawb = ?", params
            )
            results.append({
                "mawb": item.mawb,
                "status": "ok" if cur.rowcount > 0 else "not_found",
            })

    ok = sum(1 for r in results if r["status"] == "ok")
    return {"status": "ok", "updated": ok, "results": results}


@app.post("/api/import-confirm/bulk", summary="Bulk upsert scraped rows (bot ingest)")
def bulk_upsert_import_confirm(rows: List[Dict[str, Any]] = Body(...)):
    """
    Accept a JSON array of import-confirm rows scraped by the Playwright bot.
    Each row must contain at least a 'mawb' field.
    All other fields are upserted as-is (string values).
    """
    upserted = 0
    skipped = 0
    errors: List[Dict] = []

    with get_conn() as conn:
        for row in rows:
            mawb = str(row.get("mawb", "")).strip()
            if not mawb or mawb in ("", "nan", "None"):
                skipped += 1
                continue
            row["mawb"] = mawb
            # Normalise all values to str|None
            clean = {k: (str(v).strip() if v is not None and str(v).strip() not in ("", "nan", "None") else None)
                     for k, v in row.items()}
            clean["mawb"] = mawb  # always keep
            try:
                _upsert_import_confirm(conn, clean)
                upserted += 1
            except Exception as exc:
                skipped += 1
                errors.append({"mawb": mawb, "error": str(exc)})

    return {"status": "ok", "upserted": upserted, "skipped": skipped, "errors": errors}


# ─────────────────────────────────────────────────────────────────────────────
# Pickup Report read endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/pickup-report", summary="List pickup report rows")
def list_pickup_report(
    shipment_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    clauses: List[str] = []
    params: List[Any] = []

    if shipment_status:
        clauses.append("shipment_status = ?")
        params.append(shipment_status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    offset = (page - 1) * page_size

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM pickup_report {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM pickup_report {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),
        "items": rows_to_dicts(rows),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stats endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/stats", summary="Summary counts for the dashboard")
def get_stats():
    with get_conn() as conn:
        total_ic = conn.execute("SELECT COUNT(*) FROM import_confirm").fetchone()[0]
        total_pr = conn.execute("SELECT COUNT(*) FROM pickup_report").fetchone()[0]

        # Import confirm — by status
        status_rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM import_confirm GROUP BY status"
        ).fetchall()

        # Import confirm — by bot_status
        bot_rows = conn.execute(
            "SELECT bot_status, COUNT(*) as cnt FROM import_confirm GROUP BY bot_status"
        ).fetchall()

        # Import confirm — by airline (top 10)
        airline_rows = conn.execute(
            "SELECT airline, COUNT(*) as cnt FROM import_confirm "
            "WHERE airline IS NOT NULL GROUP BY airline ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

        # Import confirm — by firm_code (top 10)
        firm_rows = conn.execute(
            "SELECT firm_code, COUNT(*) as cnt FROM import_confirm "
            "WHERE firm_code IS NOT NULL GROUP BY firm_code ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

    return {
        "import_confirm": {
            "total": total_ic,
            "by_status": {r["status"] or "Unknown": r["cnt"] for r in status_rows},
            "by_bot_status": {r["bot_status"] or "pending": r["cnt"] for r in bot_rows},
            "by_airline": {r["airline"]: r["cnt"] for r in airline_rows},
            "by_firm_code": {r["firm_code"]: r["cnt"] for r in firm_rows},
        },
        "pickup_report": {
            "total": total_pr,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reset (test utility)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/reset", summary="Clear all data (test use only)")
def reset_db():
    with get_conn() as conn:
        ic_count = conn.execute("SELECT COUNT(*) FROM import_confirm").fetchone()[0]
        pr_count = conn.execute("SELECT COUNT(*) FROM pickup_report").fetchone()[0]
        conn.execute("DELETE FROM import_confirm")
        conn.execute("DELETE FROM pickup_report")
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('import_confirm','pickup_report')")
    return {
        "status": "ok",
        "cleared": {"import_confirm": ic_count, "pickup_report": pr_count},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health", summary="Health check")
def root():
    with get_conn() as conn:
        ic = conn.execute("SELECT COUNT(*) FROM import_confirm").fetchone()[0]
        pr = conn.execute("SELECT COUNT(*) FROM pickup_report").fetchone()[0]
    return {
        "status": "ok",
        "service": "Apex Workflow X-Control Mock API",
        "version": "1.0.0",
        "records": {"import_confirm": ic, "pickup_report": pr},
    }
