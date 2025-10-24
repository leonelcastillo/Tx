import sqlite3, shutil, datetime, os, sys
DB='transactions.db'
BACKUP_DIR='backups'
os.makedirs(BACKUP_DIR, exist_ok=True)
now=datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
backup_path=os.path.join(BACKUP_DIR, f'transactions.db.{now}.bak')
print('Backing up', DB, '->', backup_path)
shutil.copy2(DB, backup_path)
conn=sqlite3.connect(DB)
cur=conn.cursor()
print('\nPRAGMA table_info(transactions):')
for row in cur.execute('PRAGMA table_info(transactions)').fetchall():
    print(row)
print('\nsqlite_master create sql:')
row=cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions'").fetchone()
print(row[0] if row else 'no table found')
# detect NOT NULL on weight_kg
notnull=False
for r in cur.execute('PRAGMA table_info(transactions)').fetchall():
    if r[1]=='weight_kg' and r[3]==1:
        notnull=True
        break
if not notnull:
    print('\nweight_kg already nullable; nothing to do')
    conn.close()
    sys.exit(0)
print('\nweight_kg is NOT NULL -> performing migration')
try:
    conn.execute('BEGIN')
    # create new table with weight_kg nullable
    conn.execute('''CREATE TABLE transactions_new (
        id INTEGER PRIMARY KEY,
        name VARCHAR NOT NULL,
        phone VARCHAR,
        wallet VARCHAR,
        weight_kg FLOAT,
        address VARCHAR,
        photo VARCHAR,
        date DATETIME,
        status VARCHAR NOT NULL,
        collected_weight_kg FLOAT,
        collected_photo VARCHAR,
        collected_at DATETIME
    )''')
    # copy data
    conn.execute('''INSERT INTO transactions_new (id,name,phone,wallet,weight_kg,address,photo,date,status,collected_weight_kg,collected_photo,collected_at)
                    SELECT id,name,phone,wallet,weight_kg,address,photo,date,status,collected_weight_kg,collected_photo,collected_at FROM transactions''')
    conn.execute('DROP TABLE transactions')
    conn.execute('ALTER TABLE transactions_new RENAME TO transactions')
    conn.execute('COMMIT')
    print('Migration done')
except Exception as e:
    print('Migration failed:', e)
    try:
        conn.execute('ROLLBACK')
    except Exception:
        pass
finally:
    conn.close()
    print('Closed')
