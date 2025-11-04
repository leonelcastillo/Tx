#!/usr/bin/env python3
"""download_from_json.py

Read a transactions JSON (as returned by GET /transactions) and download all referenced
`photo` and `collected_photo` files into the app's `src/static/uploads` folder.

This script is safe by default: it will NOT overwrite existing files unless you pass
`--overwrite`. It can also create a timestamped backup of the existing uploads folder
before copying new files in.

Usage:
  python scripts/download_from_json.py --json prod_transactions.json --base-url https://myapp.onrender.com --admin-key SECRET

Options:
  --json        Path to the JSON file (required)
  --base-url    Base URL of the running service (used to download files)
  --admin-key   Admin API key to send as x-admin-key header when downloading static files
  --uploads-dir Path to local uploads folder to save files (default: src/static/uploads)
  --overwrite   Overwrite existing files in uploads dir
  --backup      Create a timestamped backup of existing uploads folder before modifying
"""
from __future__ import annotations
import argparse
import json
import os
import requests
from pathlib import Path
from datetime import datetime
import shutil


def parse_args():
    p = argparse.ArgumentParser(description='Download referenced upload files from transactions JSON')
    p.add_argument('--json', required=True, help='Path to transactions JSON file')
    p.add_argument('--base-url', required=True, help='Base URL of the running service (e.g. https://myapp.onrender.com)')
    p.add_argument('--admin-key', required=False, help='Admin API key to send in x-admin-key header')
    p.add_argument('--uploads-dir', default='src/static/uploads', help='Local uploads dir to save files')
    p.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    p.add_argument('--backup', action='store_true', help='Make timestamped backup of existing uploads folder before changes')
    return p.parse_args()


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit('Expected top-level JSON array of transactions')
    return data


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def backup_uploads(dest: Path) -> Path | None:
    if not dest.exists():
        return None
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    bak = dest.parent / (dest.name + f'.backup_{ts}')
    shutil.copytree(dest, bak)
    return bak


def download_file(url: str, dest: Path, headers: dict | None = None, overwrite: bool = False):
    if dest.exists() and not overwrite:
        return 'skipped'
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, headers=headers or {}, stream=True, timeout=30) as r:
            if r.status_code != 200:
                return f'failed:{r.status_code}'
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(1024 * 64):
                    if not chunk:
                        break
                    f.write(chunk)
        return 'ok'
    except Exception as e:
        return f'error:{e}'


def main():
    args = parse_args()
    jpath = Path(args.json)
    if not jpath.exists():
        raise SystemExit(f'JSON file not found: {jpath}')
    uploads_dir = Path(args.uploads_dir)
    if args.backup:
        bak = backup_uploads(uploads_dir)
        if bak:
            print(f'Backed up existing uploads to: {bak}')
        else:
            print('No existing uploads folder to backup')

    rows = load_json(jpath)
    files = set()
    for r in rows:
        for col in ('photo', 'collected_photo'):
            v = r.get(col)
            if v and isinstance(v, str) and v.strip() != '':
                files.add(v.strip())

    print(f'Found {len(files)} unique referenced files')
    headers = {}
    if args.admin_key:
        headers['x-admin-key'] = args.admin_key

    # download each file
    base = args.base_url.rstrip('/')
    results = {'ok': [], 'skipped': [], 'failed': []}
    for f in sorted(files):
        # if full URL
        if f.startswith('http://') or f.startswith('https://'):
            url = f
            filename = os.path.basename(f)
        else:
            url = f'{base}/static/uploads/{f}'
            filename = f
        dest = uploads_dir / filename
        res = download_file(url, dest, headers=headers, overwrite=args.overwrite)
        if res == 'ok':
            results['ok'].append(filename)
            print(f'Downloaded: {filename}')
        elif res == 'skipped':
            results['skipped'].append(filename)
            print(f'Skipped (exists): {filename}')
        else:
            results['failed'].append((filename, res))
            print(f'Failed: {filename} -> {res}')

    print('\nSummary:')
    print(f"Downloaded: {len(results['ok'])}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"Failed: {len(results['failed'])}")
    if results['failed']:
        print('Failures:')
        for fn, err in results['failed']:
            print(f'  {fn} : {err}')


if __name__ == '__main__':
    main()
