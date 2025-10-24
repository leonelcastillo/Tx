# Smoke test

Run these commands in PowerShell from the project root (where requirements.txt is).

1) Create and activate a virtualenv, install deps:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2) Initialize the database and add a test transaction via CLI:

```powershell
python -m src.cli init
python -m src.cli add --name "Smoke Tester" --phone "+100" --wallet "wallet-smoke" --weight 1.5
python -m src.cli list
```

3) Start the API server (optional) and test endpoints with curl or a browser:

```powershell
uvicorn src.main:app --reload
# then open http://127.0.0.1:8000/docs for interactive API docs
```
