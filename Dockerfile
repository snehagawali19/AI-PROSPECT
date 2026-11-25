# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=4000

WORKDIR /app

# Dependencies first (better layer caching). requirements-dev adds pytest so tests can run in the container.
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# Application code
COPY app ./app
COPY scripts ./scripts
COPY tests ./tests
COPY pytest.ini docker-entrypoint.sh ./

# Run as an unprivileged user
RUN chmod +x /app/docker-entrypoint.sh \
 && useradd --create-home --uid 10001 appuser \
 && mkdir -p /app/samples && chown -R appuser:appuser /app
USER appuser

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"4000\")}/health', timeout=4)" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["serve"]
