Purpose
-------
This folder contains small one-off helper scripts used during development and for safely synchronizing
production data into a local environment for inspection. Most scripts are read-only against the
remote service (they use the `/export.csv` or `/transactions` endpoints) and are intended to help you
backup data, import it into a safe local SQLite DB, and preview the UI locally.

Safety and disclaimers
----------------------
- Most scripts call admin endpoints and require an admin API key. Keep that key secret.
- These scripts are intended to run locally. They do not modify production state unless a script
	explicitly documents that behavior (normally they only GET resources and write local files).
- Always keep a backup of any local DB or uploads folder before replacing or overwriting them.

Scripts (short summary)
------------------------
- tmp_test_submit.py — tiny test client that POSTs a sample submission to a running local server.
- tmp_get_transactions.py — GET `/transactions` with a small limit and prints results (dev helper).
- inspect_row5.py — helper to open and print DB row #5 (local DB inspector).
- sum_collected.py — sums `collected_weight_kg` from the local DB and prints totals.

- download_prod_data.py — Download `/export.csv` and then download every file referenced in the CSV's
	`photo` and `collected_photo` columns. Produces a folder with all downloads. Usage example below.
- import_csv_to_sqlite.py — Import a CSV (like `/export.csv`) into a local SQLite DB. It makes a
	timestamped backup of the target DB before changing it and uses upserts so imports are reversible.
- convert_json_to_csv.py — Convert a JSON array (as returned by `GET /transactions`) into a CSV compatible
	with `import_csv_to_sqlite.py`. Optionally runs the importer for you.
- download_from_json.py — Read a transactions JSON and download all referenced `photo` and
	`collected_photo` files into `src/static/uploads`. Supports `--backup` and `--overwrite` flags.
- sync_prod_to_local.ps1 — PowerShell wrapper that fetches `/export.csv`, downloads referenced uploads,
	optionally attempts to fetch a raw SQLite DB from common paths, and creates a ZIP archive. Use on
	Windows (PowerShell) only.

Usage examples
--------------
Replace placeholders with your service URL and admin key where required.

1) Download export CSV and all referenced uploads (safe, read-only):

```powershell
# fetch CSV (admin key passed via api_key query param)
$base = "https://your-app.onrender.com"
$adminKey = "<ADMIN_KEY>"
Invoke-WebRequest -Uri "$base/export.csv?api_key=$adminKey" -OutFile prod_export.csv -UseBasicParsing

# download referenced uploads into a folder using the bundled script
python .\scripts\download_prod_data.py --base-url $base --admin-key $adminKey --out-csv prod_export.csv --out-uploads prod_uploads
```

2) Import the CSV into a new local DB for preview (non-destructive):

```powershell
# copy an existing schema DB if you have one, or allow the importer to create rows (ensure schema exists)
Copy-Item .\transactions.db .\transactions.prod_sync.db -Force
python .\scripts\import_csv_to_sqlite.py --csv prod_export.csv --db .\transactions.prod_sync.db
```

3) Convert transactions JSON -> CSV and import (if you used GET /transactions):

```powershell
python .\scripts\convert_json_to_csv.py --json prod_transactions.json --csv prod_from_api.csv --import --db .\transactions.prod_sync.db
```

4) Download files referenced by `prod_transactions.json` into `src/static/uploads` (recommended with backup):

```powershell
python .\scripts\download_from_json.py --json .\prod_transactions.json --base-url https://your-app.onrender.com --admin-key '<ADMIN_KEY>' --backup
```

5) One-command Windows wrapper (PowerShell) to fetch CSV, downloads and zip everything:

```powershell
.\scripts\sync_prod_to_local.ps1 -BaseUrl https://your-app.onrender.com -AdminKey '<ADMIN_KEY>'
# add -TryDownloadDb to attempt to fetch a raw DB (rare; only if exposed)
```

Post-download steps (local preview)
-----------------------------------
1. Back up your current `src/static/uploads` and `transactions.db`.
2. Copy the downloaded uploads into `src/static/uploads` (or let `download_from_json.py` write into that folder).
3. Point the app at the prod-sync DB and start it locally:

```powershell
$env:DATABASE_URL = "sqlite:///$((Join-Path $PWD 'transactions.prod_sync.db'))"
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

2. Open the admin and observer pages in your browser to visually verify collected photos, totals and the
	 per-row edit workflow.

Notes & troubleshooting
-----------------------
- If `collected_photo` values are missing from `/export.csv`, try `GET /transactions` (JSON) — it may contain
	richer fields. Use `convert_json_to_csv.py` to turn that JSON into an importable CSV.
- If some downloads fail, check whether the DB stores full external URLs (Pinata gateway). The downloader will
	try external URLs directly; you may need to adjust headers or use an alternate gateway URL.
- If you need the raw SQLite `.db` from a managed host (Render), that usually requires a snapshot or a temporary
	admin endpoint on the server — both require a redeploy or provider support. Prefer CSV+uploads unless you
	explicitly need the file.

Contact / next steps
--------------------
If you want, I can:
- Add a checksum manifest generator for uploads to validate integrity after copy.
- Add a safe merge tool to reconcile local vs prod rows with configurable conflict rules and a dry-run mode.

Replace or extend this README with any other scripts you add so future you (or collaborators) can follow the
safe workflow.  

