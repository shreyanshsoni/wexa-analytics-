FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e .

CMD ["celery", "-A", "app.workers.celery_app.celery_app", "worker", "-Q", "ingestion,celery", "-c", "2", "--loglevel=info"]
