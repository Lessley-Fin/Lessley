# Independent deal-optimizer module — layered-DAG stacking engine.
# Stage 1: base — runtime engine + CLI
FROM python:3.12-slim AS base
WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "deal_optimizer.cli"]

# Stage 2: service — HTTP surface (api.py) over the same engine
FROM base AS service
RUN pip install --no-cache-dir ".[service]"
EXPOSE 8003
ENTRYPOINT ["uvicorn"]
CMD ["deal_optimizer.api:app", "--host", "0.0.0.0", "--port", "8003"]

# Stage 3: test — adds dev deps, runs the verification suite
FROM base AS test
RUN pip install --no-cache-dir ".[dev,service]"
COPY tests/ tests/
CMD ["pytest", "--tb=short", "-q"]
