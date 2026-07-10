FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY services/gateway/requirements.txt ./services/gateway/requirements.txt
RUN pip install --no-cache-dir -r services/gateway/requirements.txt

COPY common ./common
COPY services/gateway/app ./services/gateway/app

WORKDIR /app/services/gateway

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
