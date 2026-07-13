FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY services/agent/requirements.txt ./services/agent/requirements.txt
RUN pip install --no-cache-dir -r services/agent/requirements.txt

COPY common ./common
COPY services/agent/app ./services/agent/app

WORKDIR /app/services/agent
EXPOSE 8083

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8083"]
