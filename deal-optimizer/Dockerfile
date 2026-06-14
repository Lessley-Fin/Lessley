# Independent deal-optimizer module — layered-DAG stacking engine.
# Stage 1: base — runtime engine + CLI
FROM python:3.12-slim AS base
WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "deal_optimizer.cli"]

# Stage 2: test — adds dev deps, runs the verification suite
FROM base AS test
RUN pip install --no-cache-dir ".[dev]"
COPY tests/ tests/
CMD ["pytest", "--tb=short", "-q"]
