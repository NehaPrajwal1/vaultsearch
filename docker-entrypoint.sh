#!/bin/sh
set -eu

# Generate synthetic data on first run.
if [ ! -f data/chunks.json ]; then
  echo "Building synthetic corpus..."
  python ingestion/generate_data.py
  python ingestion/ingest.py
fi

# Build indexes on first run (or if they are missing).
if [ "${VAULTSEARCH_SEARCH_ONLY:-true}" = "false" ] && { [ ! -f indexes/vectors.faiss ] || [ ! -f indexes/bm25.pkl ]; }; then
  echo "Building search indexes..."
  python indexing/build_indexes.py
fi

exec uvicorn app.api:app --host 0.0.0.0 --port 8000
