from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./transactions.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    # Create tables if they don't exist.
    Base.metadata.create_all(bind=engine)

    # If using SQLite and the transactions table already existed before we added
    # the collected_* columns, create them using ALTER TABLE so existing DBs
    # are upgraded in-place. This is a small, safe migration for the local
    # single-file SQLite used in development.
    try:
        if DATABASE_URL.startswith('sqlite'):
            with engine.connect() as conn:
                # get existing columns
                res = conn.execute(text("PRAGMA table_info(transactions)"))
                rows = res.fetchall()
                existing = {r[1] for r in rows}  # row[1] is column name
                # detect if weight_kg column is present and marked NOT NULL (pk of PRAGMA: 'notnull' at index 3)
                weight_info = None
                for r in rows:
                    if r[1] == 'weight_kg':
                        weight_info = r
                        break
                alters = []
                if 'collected_weight_kg' not in existing:
                    alters.append("ALTER TABLE transactions ADD COLUMN collected_weight_kg FLOAT")
                if 'collected_photo' not in existing:
                    alters.append("ALTER TABLE transactions ADD COLUMN collected_photo VARCHAR")
                if 'collected_at' not in existing:
                    alters.append("ALTER TABLE transactions ADD COLUMN collected_at DATETIME")
                for sql in alters:
                    conn.execute(text(sql))
                # If weight_kg exists and is NOT NULL, perform a safe table rebuild to make it nullable.
                # PRAGMA table_info returns columns as: cid, name, type, notnull, dflt_value, pk
                if weight_info is not None and weight_info[3] == 1:
                    # rebuild table with weight_kg nullable
                    try:
                        conn.execute(text("BEGIN TRANSACTION"))
                        # create a new table with desired schema (nullable weight_kg)
                        conn.execute(text(
                            "CREATE TABLE IF NOT EXISTS transactions_new ("
                            "id INTEGER PRIMARY KEY,"
                            "name VARCHAR NOT NULL,"
                            "phone VARCHAR,"
                            "wallet VARCHAR,"
                            "weight_kg FLOAT,"
                            "address VARCHAR,"
                            "photo VARCHAR,"
                            "date DATETIME,"
                            "status VARCHAR NOT NULL,"
                            "collected_weight_kg FLOAT,"
                            "collected_photo VARCHAR,"
                            "collected_at DATETIME"
                            ")"
                        ))
                        # copy data (NULLs allowed for weight_kg)
                        conn.execute(text("INSERT INTO transactions_new (id, name, phone, wallet, weight_kg, address, photo, date, status, collected_weight_kg, collected_photo, collected_at) SELECT id, name, phone, wallet, weight_kg, address, photo, date, status, collected_weight_kg, collected_photo, collected_at FROM transactions"))
                        conn.execute(text("DROP TABLE transactions"))
                        conn.execute(text("ALTER TABLE transactions_new RENAME TO transactions"))
                        conn.execute(text("COMMIT"))
                    except Exception:
                        try:
                            conn.execute(text("ROLLBACK"))
                        except Exception:
                            pass
                        # if migration fails, continue silently (startup should not crash)
    except Exception:
        # best-effort: don't fail startup if ALTER TABLE can't run (will surface on query)
        pass
