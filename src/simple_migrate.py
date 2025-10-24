"""Simple migration helper for local SQLite.

Adds missing columns (address, photo) to the transactions table so the app can write these fields.
This is intentionally small and safe for local development; it checks for column existence before ALTER.
"""
import sqlite3
import os
from . import database


def get_db_path():
    # mirror database.py default behavior
    url = os.environ.get('DATABASE_URL', 'sqlite:///./transactions.db')
    if url.startswith('sqlite:///'):
        return url.replace('sqlite:///', '')
    raise RuntimeError('This migration helper only works with a local sqlite DB')


def ensure_columns():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print('No database file found at', db_path)
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(transactions)")
    cols = [r[1] for r in cur.fetchall()]
    print('Existing columns:', cols)

    to_add = []
    if 'address' not in cols:
        to_add.append("ALTER TABLE transactions ADD COLUMN address TEXT")
    if 'photo' not in cols:
        to_add.append("ALTER TABLE transactions ADD COLUMN photo TEXT")

    if not to_add:
        print('No migration needed')
        conn.close()
        return

    for sql in to_add:
        print('Running:', sql)
        cur.execute(sql)

    conn.commit()
    conn.close()
    print('Migration complete')


if __name__ == '__main__':
    ensure_columns()
