import sqlite3, json

conn = sqlite3.connect('/app/data.db')
cur = conn.cursor()
try:
    cur.execute('SELECT COUNT(*) FROM ai_calls')
    print('ai_calls count:', cur.fetchone()[0])
    cur.execute("SELECT id, ts, substr(response_excerpt,1,200) FROM ai_calls ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    print(json.dumps(rows, ensure_ascii=False, default=str))
except Exception as e:
    print('ERROR', e)
finally:
    conn.close()
