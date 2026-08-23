FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8501
EXPOSE 8501

# Use bash -c so $PORT gets expanded at container start
CMD ["bash", "-c", "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"]
