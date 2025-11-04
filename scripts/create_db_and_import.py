#!/usr/bin/env python3
"""create_db_and_import.py

Create a new SQLite DB with the application's schema and import a CSV of transactions into it.

Usage:
  python scripts/create_db_and_import.py --db transactions.prod_sync.db --csv prod_transactions_from_api.csv

This script will:
 - create the SQLite DB file (if missing) and create tables using the SQLAlchemy models
 - call the existing importer `scripts/import_csv_to_sqlite.py` to upsert rows from the CSV

It is safe to run multiple times; the importer backs up the target DB before altering it.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine


def create_schema(db_path: Path):
    # Create the DB file and schema using the project's models
    # Import locally to avoid importing top-level app which may rely on env vars
    import importlib, sys
    # Ensure repo root is on sys.path so 'src' package can be imported
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    # load models module
    try:
        models = importlib.import_module('src.models')
    except Exception as e:
        raise RuntimeError(f"Failed to import 'src.models': {e}")
    # create engine for the provided db_path
    db_uri = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(db_uri, connect_args={"check_same_thread": False})
    # create tables
    models.Base.metadata.create_all(bind=engine)


def run_import_script(csv_path: Path, db_path: Path):
    cmd = [sys.executable, str(Path(__file__).parent / 'import_csv_to_sqlite.py'), '--csv', str(csv_path), '--db', str(db_path)]
    print('Running importer:', ' '.join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise SystemExit(f'Importer failed with exit code {res.returncode}')


def main():
    p = argparse.ArgumentParser(description='Create DB schema and import CSV into it')
    p.add_argument('--db', required=True, help='Path to target SQLite DB (will be created if missing)')
    p.add_argument('--csv', required=True, help='Path to transactions CSV to import')
    args = p.parse_args()

    dbp = Path(args.db).resolve()
    csvp = Path(args.csv).resolve()
    if not csvp.exists():
        raise SystemExit(f'CSV not found: {csvp}')

    print(f'Ensuring DB schema exists at: {dbp}')
    create_schema(dbp)
    print('Schema created/verified.')

    run_import_script(csvp, dbp)
    print('Import finished.')


if __name__ == '__main__':
    main()
