import sqlite3
import os

# Determine sqlite file from DATABASE_URL if provided, otherwise use local transactions.db
db_path = 'transactions.db'
env_db = os.environ.get('DATABASE_URL')
if env_db and env_db.startswith('sqlite'):
	if env_db.startswith('sqlite:///'):
		db_path = env_db.replace('sqlite:///', '')
	elif env_db.startswith('sqlite://'):
		db_path = env_db.replace('sqlite://', '')

con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute("SELECT COUNT(*) FROM transactions WHERE collected_weight_kg IS NOT NULL")
count = cur.fetchone()[0]
cur.execute("SELECT SUM(collected_weight_kg) FROM transactions WHERE collected_weight_kg IS NOT NULL")
sumv = cur.fetchone()[0]

# Why floating artifacts appear:
# SQLite stores REAL as IEEE-754 floating point. Summing decimal fractions
# can produce binary floating results like 50.419999999999995 even though
# the human values look like 50.42. This is normal for binary floats.

# Print a nicely formatted rounded value for display, and the raw value for
# debugging. For exact decimal arithmetic you can use the `decimal` module
# and sum Decimal(...) of the string representations.
print('collected_rows:', count)
if sumv is None:
	print('sum_collected: 0')
else:
	# human-friendly
	print('sum_collected (rounded):', f"{sumv:.2f}")
	# raw debugging value
	print('sum_collected (raw):', sumv)

con.close()
