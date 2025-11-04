#!/usr/bin/env python3
"""Export the `transactions` table from a SQLite DB to JSON and CSV files.

Usage:
  python scripts/export_db.py --db transactions.db --json-out transactions.export.json --csv-out transactions.export.csv

If an output path is omitted, the corresponding file will not be written but a summary will still be printed.
"""
from __future__ import annotations
import sqlite3
import json
import csv
import argparse
from pathlib import Path


def get_columns(conn: sqlite3.Connection, table: str = 'transactions') -> list:
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    rows = cur.fetchall()
    return [r[1] for r in rows]


def fetch_rows(conn: sqlite3.Connection, cols: list, table: str = 'transactions') -> list:
    cur = conn.execute(f"SELECT {', '.join(cols)} FROM {table}")
    rows = cur.fetchall()
    result = [dict(zip(cols, r)) for r in rows]
    return result


def write_json(path: Path, rows: list):
    path.write_text(json.dumps(rows, default=str, ensure_ascii=False, indent=2), encoding='utf-8')


def write_csv(path: Path, cols: list, rows: list):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ('' if v is None else v) for k, v in r.items()})


def main():
    p = argparse.ArgumentParser(description='Export transactions table to JSON and CSV')
    p.add_argument('--db', default='transactions.db', help='Path to SQLite DB')
    p.add_argument('--json-out', help='Write rows to this JSON file')
    p.add_argument('--csv-out', help='Write rows to this CSV file')
    args = p.parse_args()

    dbp = Path(args.db)
    if not dbp.exists():
        raise SystemExit(f'Database not found: {dbp}')

    conn = sqlite3.connect(dbp.as_posix())
    try:
        cols = get_columns(conn)
        if not cols:
            raise SystemExit('No columns found on transactions table')
        rows = fetch_rows(conn, cols)
        print(f'Fetched {len(rows)} rows with columns: {cols}')

        if args.json_out:
            outj = Path(args.json_out)
            write_json(outj, rows)
            print(f'Wrote JSON to {outj} ({outj.stat().st_size} bytes)')

        if args.csv_out:
            outc = Path(args.csv_out)
            write_csv(outc, cols, rows)
            print(f'Wrote CSV to {outc} ({outc.stat().st_size} bytes)')

    finally:
        conn.close()


if __name__ == '__main__':
    main()
