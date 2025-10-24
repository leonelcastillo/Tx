import sqlite3
conn=sqlite3.connect('transactions.db')
c=conn.cursor()
try:
    c.execute("INSERT INTO transactions (name, phone, wallet, weight_kg, address, photo, status) VALUES (?,?,?,?,?,?,?)",
              ('DirectTest', '000', None, None, 'addr', None, 'pending'))
    conn.commit()
    print('inserted id', c.lastrowid)
except Exception as e:
    print('error', type(e), e)
    import traceback
    traceback.print_exc()
finally:
    conn.close()
