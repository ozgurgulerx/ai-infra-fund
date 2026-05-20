FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/packages/core/src:/app/services/api/src

COPY pyproject.toml /app/pyproject.toml
COPY packages/core /app/packages/core
COPY services/api /app/services/api
COPY services/worker /app/services/worker
COPY config /app/config
RUN pip install --no-cache-dir -e "."

EXPOSE 8000

CMD ["python", "-m", "ai_infra_fund_api.main"]

FROM runtime AS test

COPY AGENTS.md /app/AGENTS.md
COPY .dockerignore /app/.dockerignore
COPY .env.example /app/.env.example
COPY apps/web /app/apps/web
COPY docker-compose.prod.example.yml /app/docker-compose.prod.example.yml
COPY docker-compose.yml /app/docker-compose.yml
COPY docs /app/docs
COPY scripts /app/scripts
COPY tests /app/tests
RUN pip install --no-cache-dir -e ".[dev]"

CMD ["python", "-m", "pytest", "tests/test_deployment_readiness.py"]

FROM runtime AS production

CMD ["python", "-m", "ai_infra_fund_api.main"]
