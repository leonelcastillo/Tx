Purpose: archived debug helpers and small one-off scripts used during local development.

Files:
- tmp_test_submit.py  - POSTs a simple submit to the local server (no weight)
- tmp_get_transactions.py - GET /transactions?limit=5 and prints first two results
- inspect_row5.py - (existing) small helper to inspect DB row #5
- sum_collected.py - (existing) sums collected_weight_kg from the DB

Usage examples:

# run a test submit
.venv\Scripts\python.exe scripts\tmp_test_submit.py

# fetch a few transactions
.venv\Scripts\python.exe scripts\tmp_get_transactions.py

# inspect DB row 5
.venv\Scripts\python.exe scripts\inspect_row5.py

# compute collected total
.venv\Scripts\python.exe scripts\sum_collected.py

Note: These are convenience scripts for local development only. They are not part of the production API or tests.
