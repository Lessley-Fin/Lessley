# Independent deal-optimizer module — layered-DAG stacking engine.
# Stage 1: base — runtime engine + CLI
FROM python:3.12-slim AS base
WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "deal_optimizer.cli"]

# Stage 2: service — HTTP surface (api.py) over the same engine
# Port 5003 follows the workspace convention: the container port IS the production
# port (gateway 5001, personalization 5002), and dev publishes it on 8003.
FROM base AS service
RUN pip install --no-cache-dir ".[service]"
# Port is environment-driven, same as Personalization. Overridable via APP_PORT.
ENV APP_PORT=5003
EXPOSE 5003
# The base stage's ENTRYPOINT is the CLI; clear it so this stage runs the server.
ENTRYPOINT []
# sh -c so ${APP_PORT} expands; `exec` so uvicorn replaces the shell and still
# receives SIGTERM on `docker stop`.
CMD ["sh", "-c", "exec uvicorn deal_optimizer.api:app --host 0.0.0.0 --port ${APP_PORT}"]

# Stage 3: test — adds dev deps, runs the verification suite
FROM base AS test
RUN pip install --no-cache-dir ".[dev,service]"
COPY tests/ tests/
CMD ["pytest", "--tb=short", "-q"]
