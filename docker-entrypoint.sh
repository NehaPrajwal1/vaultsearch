#!/bin/sh
set -eu

# Match API mode parsing before attempting index construction.
mode=$(printf '%s' "${VAULTSEARCH_SEARCH_ONLY:-true}" | tr '[:upper:]' '[:lower:]')
case "$mode" in
  true|false) ;;
  *) echo "VAULTSEARCH_SEARCH_ONLY must be true or false" >&2; exit 2 ;;
esac
if [ "$mode" = "false" ] && [ "${VAULTSEARCH_IMAGE_MODE:-full}" = "search" ]; then
  echo "Generation requires rebuilding with VAULTSEARCH_IMAGE_TARGET=full." >&2
  exit 2
fi

# Generate synthetic data on first run.
if [ ! -f data/chunks.json ]; then
  echo "Building synthetic corpus..."
  python ingestion/generate_data.py
  python ingestion/ingest.py
fi

# Build indexes on first run (or if they are missing).
if [ "$mode" = "false" ] && { [ ! -f indexes/vectors.faiss ] || [ ! -f indexes/bm25.pkl ]; }; then
  echo "Building search indexes..."
  python indexing/build_indexes.py
fi

exec uvicorn app.api:app --host 0.0.0.0 --port 8000
