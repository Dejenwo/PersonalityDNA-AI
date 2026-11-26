# syntax=docker/dockerfile:1
# Build context: repository root (needs assessment-content/ and ai/prompts/).
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

FROM base AS deps
WORKDIR /build
COPY services/backend/pyproject.toml ./
RUN mkdir app && touch app/__init__.py && pip install --prefix=/install .

FROM base AS runtime
RUN useradd --create-home --uid 10001 pdna
COPY --from=deps /install /usr/local
WORKDIR /srv/services/backend
COPY services/backend/app ./app
COPY services/backend/alembic ./alembic
COPY services/backend/alembic.ini ./
COPY assessment-content /srv/assessment-content
COPY ai/prompts /srv/ai/prompts
ENV PDNA_CONTENT_DIR=/srv/assessment-content PDNA_PROMPTS_DIR=/srv/ai/prompts
USER pdna
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
# Migrations run as a separate one-off step (see docker-compose.yml `migrate`), never implicitly here.
CMD ["uvicorn", "app.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
