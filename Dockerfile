FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health')"
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Explicit opt-in for embeddings, reranking and generated answers.
FROM base AS full
COPY requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
COPY . .
RUN chmod +x /app/docker-entrypoint.sh
ENV VAULTSEARCH_IMAGE_MODE=full

# The last stage is also the default for plain docker build.
FROM base AS search
COPY requirements-search.txt .
RUN pip install -r requirements-search.txt
COPY . .
RUN chmod +x /app/docker-entrypoint.sh
ENV VAULTSEARCH_IMAGE_MODE=search \
    VAULTSEARCH_SEARCH_ONLY=true
