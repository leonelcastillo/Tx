import sqlite3
con=sqlite3.connect('transactions.db')
cur=con.cursor()
cur.execute("SELECT COUNT(*) FROM transactions WHERE collected_weight_kg IS NOT NULL")
count=cur.fetchone()[0]
cur.execute("SELECT SUM(collected_weight_kg) FROM transactions WHERE collected_weight_kg IS NOT NULL")
sumv=cur.fetchone()[0]
print('collected_rows:', count)
print('sum_collected:', sumv)
con.close()
