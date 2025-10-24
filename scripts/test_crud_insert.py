from src import crud, schemas, database
from sqlalchemy.orm import Session
from src import models

print('opening session')
db = database.SessionLocal()
try:
    tx_in = schemas.TransactionCreate(name='crudtest', phone='000', wallet=None, weight_kg=None, address='addr', photo=None)
    print('calling create_transaction')
    tx = crud.create_transaction(db, tx_in)
    print('created', tx.id)
except Exception as e:
    import traceback
    print('error', type(e), e)
    traceback.print_exc()
finally:
    db.close()

# print PRAGMA
import sqlite3, pprint
conn = sqlite3.connect('transactions.db')
rows = list(conn.execute('PRAGMA table_info(transactions)'))
pprint.pprint(rows)
conn.close()
