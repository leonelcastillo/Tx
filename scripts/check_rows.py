import sqlite3, os, json

db='transactions.db'
if not os.path.exists(db):
    print('No DB found at', db)
    raise SystemExit(1)
conn=sqlite3.connect(db)
cur=conn.cursor()
cur.execute('SELECT id,name,photo,weight_kg,address,date,status FROM transactions ORDER BY id DESC LIMIT 10')
rows=cur.fetchall()
out=[]
for r in rows:
    id,name,photo,weight,address,date,status = r
    url = None
    if photo:
        url = f"/static/uploads/{photo}"
    out.append({
        'id':id,
        'name':name,
        'photo':photo,
        'url':url,
        'weight_kg':weight,
        'address':address,
        'date':date,
        'status':status,
    })
print(json.dumps(out, ensure_ascii=False, indent=2))
conn.close()
