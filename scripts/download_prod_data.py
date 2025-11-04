#!/usr/bin/env python3
"""
download_prod_data.py

Download production export (CSV) and referenced upload files from a running service (Render).

Usage:
  python scripts/download_prod_data.py --base-url https://your-service.onrender.com --admin-key YOUR_KEY --out-csv prod_export.csv --out-uploads uploads

This will fetch /export.csv (using ?api_key= or x-admin-key header) and then download files referenced in the CSV's photo/collected_photo columns.
"""
from __future__ import annotations
import argparse
import csv
import os
import requests
from urllib.parse import urljoin, urlparse


def fetch_csv(base_url: str, admin_key: str | None, out_csv: str) -> None:
    params = {}
    headers = {}
    if admin_key:
        # try header and also api_key param for compatibility
        headers['x-admin-key'] = admin_key
        params['api_key'] = admin_key

    url = urljoin(base_url, '/export.csv')
    print(f"Fetching CSV from: {url}")
    r = requests.get(url, params=params, headers=headers, stream=True, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch CSV: {r.status_code} {r.text}")
    with open(out_csv, 'wb') as f:
        for chunk in r.iter_content(1024 * 64):
            if not chunk:
                break
            f.write(chunk)
    print(f"Saved CSV to {out_csv}")


def download_file(url: str, dest: str, headers: dict | None = None, overwrite: bool = False) -> None:
    if os.path.exists(dest) and not overwrite:
        print(f"Skipping existing: {dest}")
        return
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    with requests.get(url, headers=headers or {}, stream=True, timeout=30) as r:
        if r.status_code != 200:
            print(f"Warning: failed to download {url}: {r.status_code}")
            return
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(1024 * 64):
                if not chunk:
                    break
                f.write(chunk)
    print(f"Downloaded {url} -> {dest}")


def is_url(s: str) -> bool:
    try:
        p = urlparse(s)
        return bool(p.scheme and p.netloc)
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description='Download prod CSV export and uploads')
    parser.add_argument('--base-url', required=True, help='Base URL of the running service, e.g. https://myapp.onrender.com')
    parser.add_argument('--admin-key', required=False, help='Admin API key (x-admin-key)')
    parser.add_argument('--out-csv', default='prod_export.csv', help='Path to save CSV')
    parser.add_argument('--out-uploads', default='prod_uploads', help='Directory to save uploads')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    args = parser.parse_args()

    fetch_csv(args.base_url, args.admin_key, args.out_csv)

    headers = {}
    if args.admin_key:
        headers['x-admin-key'] = args.admin_key

    # parse CSV and download photo fields
    with open(args.out_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} rows in CSV. Scanning for photo fields...")
    for r in rows:
        for col in ('photo', 'collected_photo'):
            val = (r.get(col) or '').strip()
            if not val:
                continue
            if is_url(val):
                url = val
                filename = os.path.basename(urlparse(val).path)
            else:
                # assume relative uploads path
                filename = val
                url = urljoin(args.base_url, f'/static/uploads/{filename}')
            dest = os.path.join(args.out_uploads, filename)
            download_file(url, dest, headers=headers, overwrite=args.overwrite)

    print('Done.')


if __name__ == '__main__':
    main()
