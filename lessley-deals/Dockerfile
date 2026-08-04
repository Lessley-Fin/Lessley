# Stage 1: base — HTTP scrapers, normalization, matching, CLI
FROM python:3.12-slim AS base
WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY data/seed/ data/seed/
RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "lessley_deals.cli.main"]

# Stage 2: test — adds dev dependencies
FROM base AS test
RUN pip install --no-cache-dir ".[dev]"
COPY tests/ tests/
CMD ["pytest", "--tb=short", "-q"]

# Stage 3: browser — adds Playwright + Chromium
FROM base AS browser
RUN pip install --no-cache-dir ".[browser]" && \
    playwright install --with-deps chromium
ENTRYPOINT ["python", "-m", "lessley_deals.cli.main"]

# Stage 4: worker — the long-running scheduler process.
# Built on `browser` so JS-heavy sources work; swap to `base` if none are enabled.
FROM browser AS worker

# Run as a non-root user: this container talks to the open internet all day.
RUN useradd --create-home --uid 10001 scraper && chown -R scraper:scraper /app
USER scraper

ENV DEALS_STORAGE=mongo \
    DEALS_VERSIONING=1 \
    DEALS_MAX_CONCURRENCY=3 \
    DEALS_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

# Liveness: the process is healthy if the schedule still resolves.
HEALTHCHECK --interval=60s --timeout=15s --start-period=20s --retries=3 \
    CMD python -m lessley_deals.cli.main schedules > /dev/null || exit 1

# No shell wrapper, so SIGTERM reaches Python and the graceful shutdown runs.
ENTRYPOINT ["python", "-m", "lessley_deals.scheduling.service"]
