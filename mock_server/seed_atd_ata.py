"""Populate the Update ATD&ATA grid on a running backend.

`seed_fixtures()` fills this table at startup only when the process can read
`assets/apex-data.js`. A deployment whose build context is `mock_server/` alone
-- Railway with Root Directory set there -- does not ship that file, so the
grid comes up empty and SOP #2 has nothing to write against. This pushes the
same fixture rows in over the API instead.

    python seed_atd_ata.py                       # against localhost:8090
    python seed_atd_ata.py --api https://…       # against a deployment
    python seed_atd_ata.py --dry-run             # show what would be sent

Upserts on MAWB, so re-running it is safe.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

FIXTURE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "assets", "apex-data.js"
)

#: assets/apex-data.js key -> atd_ata column. Mirrors ATD_JS_TO_DB in main.py.
JS_TO_DB = {
    "mawb": "mawb", "hawb": "hawb", "customer": "customer", "airline": "airline",
    "flight": "flight", "status": "status", "pol": "pol", "pod": "pod",
    "slaDate": "sla_date", "etdOrig": "etd_orig", "eta": "eta",
    "atd": "atd", "ata": "ata",
}


def read_fixture_rows() -> list[dict]:
    """Pull `var ATD_ATA_DATA = [ ... ];` out of the fixture, as main.py does."""
    with io.open(FIXTURE, encoding="utf-8") as handle:
        js = handle.read()
    match = re.search(r"var ATD_ATA_DATA = (\[.*?\n  \]);", js, re.S)
    if not match:
        raise SystemExit(f"ATD_ATA_DATA not found in {FIXTURE}")
    return json.loads(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8090",
                        help="Backend base URL (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the payload instead of sending it")
    args = parser.parse_args()

    rows = [
        {db: row.get(js, "") for js, db in JS_TO_DB.items()}
        for row in read_fixture_rows()
    ]
    rows = [r for r in rows if r.get("mawb")]
    print(f"{len(rows)} row(s) from the fixture")

    if args.dry_run:
        print(json.dumps(rows, indent=1)[:2000])
        return 0

    url = args.api.rstrip("/") + "/api/atd-ata/bulk"
    request = urllib.request.Request(
        url,
        data=json.dumps(rows).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            print(json.dumps(json.load(response), indent=1))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:400]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
