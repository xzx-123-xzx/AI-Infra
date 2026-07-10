FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY services/rag/requirements.txt ./services/rag/requirements.txt
COPY services/rag/requirements-bge.txt ./services/rag/requirements-bge.txt

RUN pip install --no-cache-dir -r services/rag/requirements.txt \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r services/rag/requirements-bge.txt

COPY common ./common
COPY services/rag/app ./services/rag/app

WORKDIR /app/services/rag

EXPOSE 8081

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
