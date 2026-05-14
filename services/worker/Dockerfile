FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/packages/core/src:/app/services/worker/src

COPY pyproject.toml /app/pyproject.toml
COPY packages/core /app/packages/core
COPY services/api /app/services/api
COPY services/worker /app/services/worker
COPY config /app/config
RUN pip install --no-cache-dir -e "."

CMD ["python", "-m", "ai_infra_fund_worker.main"]
