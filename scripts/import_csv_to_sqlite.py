#!/usr/bin/env python3
"""
import_csv_to_sqlite.py

Import transactions from a CSV (like /export.csv) into the local SQLite DB (transactions.db).

It performs a safe backup of the existing DB before making changes and uses INSERT OR REPLACE to upsert rows by id.

Usage:
  python scripts/import_csv_to_sqlite.py --csv prod_export.csv --db transactions.db

Be careful: test this on a copy of your DB first.
"""
from __future__ import annotations
import argparse
import csv
import shutil
import sqlite3
import os
from datetime import datetime


def backup_db(db_path: str) -> str:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB not found: {db_path}")
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    bak = f"{db_path}.bak.{timestamp}"
    shutil.copy2(db_path, bak)
    print(f"Backup created: {bak}")
    return bak


def read_csv_rows(csv_path: str) -> list[dict]:
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [r for r in reader]


def upsert_rows(db_path: str, rows: list[dict]):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Build flexible insert based on available columns
        for r in rows:
            # map only known columns
            cols = []
            vals = []
            for col in ('id','name','phone','wallet','weight_kg','address','photo','date','status','collected_weight_kg','collected_photo','collected_at'):
                if col in r and r[col] != '':
                    cols.append(col)
                    vals.append(r[col])
            if not cols:
                continue
            placeholders = ','.join('?' for _ in cols)
            col_list = ','.join(cols)
            # Use INSERT OR REPLACE to upsert by primary key (id). If id not provided, let DB autoincrement.
            if 'id' in cols:
                sql = f"INSERT OR REPLACE INTO transactions ({col_list}) VALUES ({placeholders})"
                cur.execute(sql, vals)
            else:
                # insert without id - skip if identical row exists is hard; just insert
                sql = f"INSERT INTO transactions ({col_list}) VALUES ({placeholders})"
                cur.execute(sql, vals)
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Import CSV export into local SQLite DB')
    parser.add_argument('--csv', required=True, help='Path to CSV file')
    parser.add_argument('--db', default='transactions.db', help='Path to SQLite DB')
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        raise FileNotFoundError(f"CSV not found: {args.csv}")

    if os.path.exists(args.db):
        print('Backing up DB...')
        backup_db(args.db)
    else:
        print('DB does not exist locally; a new DB will be created by the insert statements (ensure schema exists).')

    rows = read_csv_rows(args.csv)
    print(f"Read {len(rows)} rows from CSV. Importing into {args.db}...")
    upsert_rows(args.db, rows)
    print('Import complete.')


if __name__ == '__main__':
    main()
