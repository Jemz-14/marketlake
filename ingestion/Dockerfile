# syntax=docker/dockerfile:1

# --- MarketLake ingestion image ------------------------------------------
# Containerises the Phase 1 bronze extractor so it runs anywhere without a
# local Python setup -- and lifts straight into an Azure Container Apps job
# later. Build context is this ingestion/ directory.
FROM python:3.11-slim

# Predictable Python behaviour in containers:
#   - no .pyc clutter; unbuffered stdout so `docker logs` streams live
#   - LAKE_ROOT points the job at the mounted data volume by default
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LAKE_ROOT=/data

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (see .dockerignore for what's excluded).
COPY . .

# Run as a non-root user; pre-create the lake mount point and hand it over.
RUN useradd --create-home --uid 1000 appuser \
 && mkdir -p /data \
 && chown -R appuser:appuser /app /data
USER appuser

# `docker run <image> [args]` runs the job; any args are appended to extract.py,
# e.g. `docker run marketlake-ingest --sources fx --full-refresh`.
ENTRYPOINT ["python", "extract.py"]
