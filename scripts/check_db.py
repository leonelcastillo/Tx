import sqlite3, os, pprint
db = 'transactions.db'
print('DB exists:', os.path.exists(db))
if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(transactions)')
    rows = cur.fetchall()
    pprint.pprint(rows)
    conn.close()
