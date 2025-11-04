#!/usr/bin/env python3
"""Cleanup uploads folder.

Scans the uploads directory (default: src/static/uploads) and the SQLite DB (default: transactions.db)
and deletes any files that are not referenced by `photo` or `collected_photo` columns in the `transactions` table.

Usage:
  python scripts/cleanup_uploads.py [--db PATH] [--uploads PATH] [--dry-run] [--yes] [--verbose]

By default the script runs in dry-run mode and will only list candidates. Use --yes to actually delete files.
"""
from __future__ import annotations
import argparse
import os
import sqlite3
from typing import Set


def gather_referenced_files(db_path: str) -> Set[str]:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT photo, collected_photo FROM transactions")
        rows = cur.fetchall()
    finally:
        conn.close()

    referenced = set()
    for a, b in rows:
        for v in (a, b):
            if not v:
                continue
            v = str(v).strip()
            # if value looks like a URL, extract basename; otherwise treat value as filename
            # examples: gateway URLs, ipfs paths, or plain filenames
            base = os.path.basename(v)
            if base:
                referenced.add(base)
    return referenced


def find_unused(upload_dir: str, referenced: Set[str]) -> list:
    if not os.path.isdir(upload_dir):
        raise FileNotFoundError(f"Uploads directory not found: {upload_dir}")
    candidates = []
    for name in os.listdir(upload_dir):
        path = os.path.join(upload_dir, name)
        if not os.path.isfile(path):
            continue
        if name not in referenced:
            candidates.append(path)
    return sorted(candidates)


def main():
    root = os.path.dirname(os.path.dirname(__file__))
    parser = argparse.ArgumentParser(description="Cleanup unused uploads in src/static/uploads by comparing against DB references")
    # default DB: prefer DATABASE_URL when set (sqlite:/// style), otherwise use ./transactions.db
    env_db = os.environ.get('DATABASE_URL')
    default_db = os.path.join(root, "transactions.db")
    if env_db and env_db.startswith('sqlite'):
        # support sqlite:///./transactions.db and sqlite:////absolute/path
        if env_db.startswith('sqlite:///'):
            default_db = env_db.replace('sqlite:///', '')
        elif env_db.startswith('sqlite://'):
            default_db = env_db.replace('sqlite://', '')

    # default uploads dir: allow UPLOAD_DIR env var to override for persistent mounts
    default_uploads = os.environ.get('UPLOAD_DIR', os.path.join(root, 'src', 'static', 'uploads'))

    parser.add_argument("--db", default=default_db, help="Path to sqlite transactions DB")
    parser.add_argument("--uploads", default=default_uploads, help="Uploads directory to scan")
    parser.add_argument("--dry-run", action="store_true", default=True, dest="dry_run", help="Only list files that would be deleted (default)")
    parser.add_argument("--yes", action="store_true", help="Actually delete files (implies --no-dry-run)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Adjust dry-run depending on --yes
    dry_run = not args.yes

    print(f"DB: {args.db}")
    print(f"Uploads dir: {args.uploads}")
    try:
        referenced = gather_referenced_files(args.db)
    except Exception as e:
        print(f"Error reading DB: {e}")
        return 2

    if args.verbose:
        print(f"Referenced filenames (count={len(referenced)}):")
        for r in sorted(referenced):
            print("  ", r)

    try:
        candidates = find_unused(args.uploads, referenced)
    except Exception as e:
        print(f"Error scanning uploads dir: {e}")
        return 2

    if not candidates:
        print("No orphaned files found. Nothing to do.")
        return 0

    print(f"Found {len(candidates)} candidate(s) for deletion:")
    for p in candidates:
        print("  ", p)

    if dry_run:
        print('\nDry-run mode: no files were deleted. Rerun with --yes to delete.')
        return 0

    # confirm one last time
    ok = True
    try:
        for p in candidates:
            try:
                os.remove(p)
                if args.verbose:
                    print(f"Deleted: {p}")
            except Exception as e:
                print(f"Failed to delete {p}: {e}")
                ok = False
    except KeyboardInterrupt:
        print("Aborted by user")
        return 3

    if ok:
        print("Deletion complete.")
        return 0
    else:
        print("Completed with some failures.")
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
