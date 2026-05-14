FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/packages/core/src:/app/services/worker/src

COPY packages/core /app/packages/core
COPY services/worker /app/services/worker
COPY config /app/config
RUN pip install --no-cache-dir -r /app/services/worker/requirements.txt

CMD ["python", "-m", "ai_infra_fund_worker.main"]
