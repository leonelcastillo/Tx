#!/usr/bin/env python3
"""merge_dbs.py

Dry-run merge helper that compares two SQLite databases' `transactions` tables and reports
differences. It can optionally produce SQL statements to apply the production changes to the
local DB, and can apply them (with a backup) when --apply is used.

Usage (dry-run):
  python scripts/merge_dbs.py --prod-db transactions.prod_sync.db --local-db transactions.db

Generate SQL and apply (BE CAREFUL):
  python scripts/merge_dbs.py --prod-db transactions.prod_sync.db --local-db transactions.db --sql-out prod_to_local.sql --apply --backup

By default the script only prints a summary and example diffs. Use --apply only when you're ready
to modify the local DB. The script will back up the local DB when --backup is provided.
"""
from __future__ import annotations
import argparse
import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime


def get_columns(conn: sqlite3.Connection, table: str = 'transactions') -> list:
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    rows = cur.fetchall()
    return [r[1] for r in rows]


def load_rows(conn: sqlite3.Connection, cols: list) -> dict:
    cur = conn.execute(f"SELECT {', '.join(cols)} FROM transactions")
    rows = cur.fetchall()
    result = {}
    for r in rows:
        # Map column -> value
        row = dict(zip(cols, r))
        # assume id exists
        pk = row.get('id')
        if pk is None:
            # skip rows without id (unlikely) but keep a numeric index
            continue
        result[int(pk)] = row
    return result


def row_diff(local: dict, prod: dict, cols: list) -> dict:
    diffs = {}
    for c in cols:
        lv = local.get(c)
        pv = prod.get(c)
        # normalize types to comparable representations
        if isinstance(lv, float) and lv.is_integer():
            lv = float(lv)
        if isinstance(pv, float) and pv.is_integer():
            pv = float(pv)
        if lv != pv:
            diffs[c] = {'local': lv, 'prod': pv}
    return diffs


def make_insert_sql(cols: list, row: dict) -> str:
    cols_list = ', '.join([f'"{c}"' for c in cols if c in row and row[c] is not None])
    vals = []
    for c in cols:
        if c in row and row[c] is not None:
            v = row[c]
            if isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                vals.append("'" + str(v).replace("'", "''") + "'")
    vals_list = ', '.join(vals)
    sql = f"INSERT OR REPLACE INTO transactions ({cols_list}) VALUES ({vals_list});"
    return sql


def make_update_sql(pk: int, diffs: dict) -> str:
    parts = []
    for c, v in diffs.items():
        pv = v['prod']
        if pv is None:
            parts.append(f'"{c}" = NULL')
        elif isinstance(pv, (int, float)):
            parts.append(f'"{c}" = {pv}')
        else:
            parts.append(f'"{c}" = ' + "'" + str(pv).replace("'", "''") + "'")
    set_clause = ', '.join(parts)
    sql = f"UPDATE transactions SET {set_clause} WHERE id = {pk};"
    return sql


def backup_file(path: Path) -> Path:
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    bak = path.with_name(path.name + f'.bak.{ts}')
    shutil.copy2(path, bak)
    return bak


def main():
    p = argparse.ArgumentParser(description='Dry-run merge helper for transactions SQLite DBs')
    p.add_argument('--prod-db', required=True, help='Path to production-synced DB (source of truth)')
    p.add_argument('--local-db', required=True, help='Path to local DB to compare/patch')
    p.add_argument('--sql-out', help='Write SQL patch to this file (optional)')
    p.add_argument('--apply', action='store_true', help='Apply generated SQL to the local DB (dangerous)')
    p.add_argument('--backup', action='store_true', help='When --apply, backup local DB first')
    args = p.parse_args()

    prod_path = Path(args.prod_db)
    local_path = Path(args.local_db)
    if not prod_path.exists():
        raise SystemExit(f'Prod DB not found: {prod_path}')
    if not local_path.exists():
        raise SystemExit(f'Local DB not found: {local_path}')

    prod_conn = sqlite3.connect(prod_path.as_posix())
    local_conn = sqlite3.connect(local_path.as_posix())
    try:
        prod_cols = get_columns(prod_conn)
        local_cols = get_columns(local_conn)
        # Use intersection to avoid columns present in one but not the other
        cols = [c for c in prod_cols if c in local_cols]
        if 'id' not in cols:
            raise SystemExit('No id column found in transactions table')

        prod_rows = load_rows(prod_conn, cols)
        local_rows = load_rows(local_conn, cols)

        prod_ids = set(prod_rows.keys())
        local_ids = set(local_rows.keys())

        only_in_prod = sorted(prod_ids - local_ids)
        only_in_local = sorted(local_ids - prod_ids)
        in_both = sorted(prod_ids & local_ids)

        print(f'Prod rows: {len(prod_ids)}, Local rows: {len(local_ids)}')
        print(f'Only in prod: {len(only_in_prod)}, only in local: {len(only_in_local)}, in both: {len(in_both)}')

        diffs = {}
        for pk in in_both:
            d = row_diff(local_rows[pk], prod_rows[pk], cols)
            if d:
                diffs[pk] = d

        print(f'Rows with differences: {len(diffs)}')

        # Prepare SQL
        sql_statements = []
        # Inserts for prod-only
        for pk in only_in_prod:
            sql_statements.append(make_insert_sql(cols, prod_rows[pk]))

        # Updates for differing rows
        for pk, d in diffs.items():
            sql_statements.append(make_update_sql(pk, d))

        # Summary printing: show small sample of diffs
        if only_in_prod:
            print('\nSample rows only in prod (ids):', only_in_prod[:10])
        if only_in_local:
            print('\nSample rows only in local (ids):', only_in_local[:10])
        if diffs:
            print('\nSample diffs:')
            count = 0
            for pk, d in list(diffs.items())[:10]:
                print(f'  id={pk}:')
                for col, v in d.items():
                    print(f'    {col}: local={v["local"]!r} --> prod={v["prod"]!r}')
                count += 1
            print(f'  (showing {count} of {len(diffs)} diffs)')

        if args.sql_out:
            outp = Path(args.sql_out)
            outp.write_text('\n'.join(sql_statements), encoding='utf-8')
            print(f'Wrote {len(sql_statements)} SQL statements to {outp}')

        if args.apply:
            if not sql_statements:
                print('No SQL to apply.')
            else:
                if args.backup:
                    bak = backup_file(local_path)
                    print(f'Local DB backed up to: {bak}')
                print('Applying SQL statements to local DB...')
                cur = local_conn.cursor()
                for s in sql_statements:
                    cur.execute(s)
                local_conn.commit()
                print('Apply complete.')

    finally:
        prod_conn.close()
        local_conn.close()


if __name__ == '__main__':
    main()
