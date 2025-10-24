import sqlite3, json
con=sqlite3.connect('transactions.db')
cur=con.cursor()
cur.execute('PRAGMA table_info(transactions)')
cols=[r[1] for r in cur.fetchall()]
cur.execute('SELECT * FROM transactions WHERE id=5')
row=cur.fetchone()
print('columns:', cols)
print('row:', row)
if row:
    print('as dict:', json.dumps(dict(zip(cols,row)), default=str))
con.close()
