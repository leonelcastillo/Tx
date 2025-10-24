# Plastic Bottle Transactions (local)

Simple Python project to record transactions when people give plastic bottles. Uses SQLite, SQLAlchemy, FastAPI and a small CLI.

Files:
- `src/` - application code
- `docs/suggestions.md` - suggestions and next steps

Quick start (Windows PowerShell):

1. Create a venv and install dependencies

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. Run the API server:

```powershell
uvicorn src.main:app --reload
```

3. Use the CLI to add/list transactions:

```powershell
python -m src.cli add --name "Juan" --phone "+123" --wallet "0xabc" --weight 2.5
python -m src.cli list
```

Smoke test (all steps):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt;
python -m src.cli init;
python -m src.cli add --name "Test User" --phone "+100" --wallet "wallet1" --weight 1.2;
python -m src.cli list;
```

```
