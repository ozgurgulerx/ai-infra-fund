FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/packages/core/src:/app/services/api/src

COPY packages/core /app/packages/core
COPY services/api /app/services/api
COPY config /app/config
RUN pip install --no-cache-dir -r /app/services/api/requirements.txt

EXPOSE 8000

CMD ["python", "-m", "ai_infra_fund_api.main"]
