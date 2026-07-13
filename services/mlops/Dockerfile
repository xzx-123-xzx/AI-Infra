FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY services/mlops/requirements.txt ./services/mlops/requirements.txt
RUN pip install --no-cache-dir -r services/mlops/requirements.txt

COPY common ./common
COPY services/mlops/app ./services/mlops/app

WORKDIR /app/services/mlops
EXPOSE 8084
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8084"]
