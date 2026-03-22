# Stage 1: base — HTTP scrapers, normalization, matching, CLI
FROM python:3.12-slim AS base
WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY data/seed/ data/seed/

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
