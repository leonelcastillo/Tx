# archived debug helper: fetch a short list of transactions
# Usage: .venv\Scripts\python.exe scripts\tmp_get_transactions.py
import requests
r = requests.get('http://127.0.0.1:8000/transactions?limit=5', timeout=10)
print(r.status_code)
print(r.json()[:2])
