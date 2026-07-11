FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Сначала только код пакета app, потом установка (alembic — не Python-пакет)
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
