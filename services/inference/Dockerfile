FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY services/inference/requirements.txt ./services/inference/requirements.txt
RUN pip install --no-cache-dir -r services/inference/requirements.txt

COPY common ./common
COPY services/inference/app ./services/inference/app

WORKDIR /app/services/inference
EXPOSE 8082

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]
