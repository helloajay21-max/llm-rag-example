import sqlite3
import pandas as pd
import os

proj = os.path.dirname(os.path.dirname(__file__))
sample_csv = os.path.join(proj, 'sample_data.csv')
db_path = os.path.join(proj, 'data.db')

print(f"sample_csv={sample_csv}\ndb_path={db_path}")

df = pd.read_csv(sample_csv)
# Ensure Date is text
if 'Date' in df.columns:
    df['Date'] = df['Date'].astype(str)

conn = sqlite3.connect(db_path)
conn.execute('CREATE TABLE IF NOT EXISTS sales (Date TEXT, Category TEXT, Value REAL)')
conn.executemany('INSERT INTO sales (Date,Category,Value) VALUES (?,?,?)', df[['Date','Category','Value']].itertuples(index=False, name=None))
conn.commit()
conn.close()
print('DB initialized.')
