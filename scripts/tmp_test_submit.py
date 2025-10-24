# archived debug helper: submit a simple transaction (no weight) to the local server
# Usage: .venv\Scripts\python.exe scripts\tmp_test_submit.py
import requests
r = requests.post('http://127.0.0.1:8000/submit', data={'name':'TestNoWeight','phone':'000','address':'home'}, timeout=10)
print(r.status_code)
print(r.text)
