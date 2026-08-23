import sqlite3

conn = sqlite3.connect('/app/data.db')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS ai_calls (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, request_json TEXT, response_excerpt TEXT)')
conn.commit()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_calls'")
print('ai_calls exists:', cur.fetchone() is not None)
conn.close()
