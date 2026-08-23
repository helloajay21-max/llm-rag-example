import os, json, sqlite3, requests, datetime

DB = '/app/data.db'
OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_KEY:
    print('NO_KEY')
    raise SystemExit(1)

# Query DB for a brief summary
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT Category, COUNT(*) as cnt, ROUND(AVG(Value),2) as avg_value, ROUND(MIN(Value),2) as min_value, ROUND(MAX(Value),2) as max_value FROM sales GROUP BY Category")
rows = cur.fetchall()
conn.close()

summary_lines = []
for r in rows:
    summary_lines.append(f"Category={r[0]} count={r[1]} avg={r[2]} min={r[3]} max={r[4]}")
summary_text = "; ".join(summary_lines) if summary_lines else 'No data'

# Build messages with system + data summary + user prompt
messages = [
    {"role":"system","content":"You are an assistant that summarizes DB query results and provides concise numeric insights and one recommendation."},
    {"role":"user","content": f"DB_QUERY_SUMMARY: {summary_text}"},
    {"role":"user","content": "Based on the DB summary above, give a short high-level summary and one actionable recommendation."}
]

body = {"model":"gpt-3.5-turbo","messages":messages,"max_tokens":300,"temperature":0.2}
headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}

# Log request preview
try:
    with open('/app/ai_calls.log','a',encoding='utf8') as fh:
        fh.write(json.dumps({"ts": datetime.datetime.utcnow().isoformat() + 'Z', "request_preview": {"model": body['model'], "messages": messages}}, ensure_ascii=False) + "\n")
except:
    pass

# Call OpenAI
resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=body, timeout=30)
resp.raise_for_status()
respj = resp.json()
assistant = respj['choices'][0]['message']['content'] if 'choices' in respj and respj['choices'] else str(respj)

# Log response excerpt
try:
    with open('/app/ai_calls.log','a',encoding='utf8') as fh:
        fh.write(json.dumps({"ts": datetime.datetime.utcnow().isoformat() + 'Z', "response_excerpt": assistant[:800]}, ensure_ascii=False) + "\n")
except:
    pass

print('---ASSISTANT_RESPONSE_START---')
print(assistant)
print('---ASSISTANT_RESPONSE_END---')
