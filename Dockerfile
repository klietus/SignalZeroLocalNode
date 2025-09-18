FROM python:3.11-slim

WORKDIR /app

# Copy agency loop
COPY app/agency_loop.py app/agency_loop.py

# Add cron launcher script
COPY scripts/agency-entrypoint.sh /agency-entrypoint.sh
RUN chmod +x /agency-entrypoint.sh

ENTRYPOINT ["/agency-entrypoint.sh"]
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Add inside Dockerfile after base install
RUN pip install redis faiss-cpu sentence-transformers

# Inside your Dockerfile (optional)
RUN curl http://ollama:11434/api/pull -d '{"name": "llama3"}'

COPY app/ ./app

CMD ["python", "app/main.py"]