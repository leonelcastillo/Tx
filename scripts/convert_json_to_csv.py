#!/usr/bin/env python3
"""convert_json_to_csv.py

Convert a JSON array of transaction objects (as returned by GET /transactions) into a CSV
suitable for `import_csv_to_sqlite.py`, and optionally import it into a SQLite DB.

Usage:
  python scripts/convert_json_to_csv.py --json prod_transactions.json --csv out.csv --db transactions.prod_sync.db --import

The script is tolerant of missing fields and will output columns expected by the importer:
id,name,phone,wallet,weight_kg,address,photo,date,status,collected_weight_kg,collected_photo,collected_at
"""
from __future__ import annotations
import argparse
import json
import csv
import subprocess
import sys
from pathlib import Path


DEFAULT_COLS = [
    'id', 'name', 'phone', 'wallet', 'weight_kg', 'address', 'photo', 'date', 'status',
    'collected_weight_kg', 'collected_photo', 'collected_at'
]


def load_json(path: Path) -> list[dict]:
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit('Expected JSON array at top level')
    return data


def write_csv(rows: list[dict], out: Path, cols: list[str] = DEFAULT_COLS):
    with out.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            row = []
            for c in cols:
                v = r.get(c, '')
                # normalize None -> empty string
                if v is None:
                    v = ''
                # ensure primitive types become strings
                row.append(v)
            w.writerow(row)


def run_import(csv_path: Path, db_path: Path):
    # Call the existing import script in this repo
    cmd = [sys.executable, str(Path(__file__).parent / 'import_csv_to_sqlite.py'), '--csv', str(csv_path), '--db', str(db_path)]
    print('Running importer:', ' '.join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise SystemExit(f'Importer failed with exit code {res.returncode}')


def main():
    p = argparse.ArgumentParser(description='Convert JSON transactions to CSV and optionally import into SQLite')
    p.add_argument('--json', required=True, help='Path to input JSON file (array of objects)')
    p.add_argument('--csv', required=False, help='Path to write CSV output (defaults to same dirname with .csv)')
    p.add_argument('--db', required=False, help='Path to SQLite DB to import into (if --import)')
    p.add_argument('--import', dest='do_import', action='store_true', help='Invoke import_csv_to_sqlite.py after conversion')
    args = p.parse_args()

    jsonp = Path(args.json)
    if not jsonp.exists():
        raise SystemExit(f'JSON file not found: {jsonp}')
    rows = load_json(jsonp)

    csvp = Path(args.csv) if args.csv else jsonp.with_suffix('.csv')
    write_csv(rows, csvp)
    print(f'Wrote CSV: {csvp} ({len(rows)} rows)')

    if args.do_import:
        if not args.db:
            raise SystemExit('When using --import you must pass --db target path')
        dbp = Path(args.db)
        # ensure folder exists
        if not dbp.parent.exists():
            dbp.parent.mkdir(parents=True, exist_ok=True)
        run_import(csvp, dbp)


if __name__ == '__main__':
    main()
