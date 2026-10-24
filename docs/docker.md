# Container setup and validation

The default image serves the synthetic keyword demo using `requirements-search.txt`. It does not install Torch, sentence-transformers or FAISS, and default Compose starts only VaultSearch. A search image rejects generation mode before attempting to build indexes. Docker Desktop must be running a Linux engine. Container runtime validation remains incomplete.

## Search demo

Copy `.env.example` to `.env` if you do not already have one. Set a known `VAULTSEARCH_USER` and a fresh `VAULTSEARCH_TOKEN` of at least 32 characters. Retain `VAULTSEARCH_IMAGE_TARGET=search` and `VAULTSEARCH_SEARCH_ONLY=true`.

```powershell
docker compose up --build vaultsearch
```

Open http://127.0.0.1:8000 and connect with the configured token. Stop foreground Compose with Ctrl+C. Compose retains its named cache volumes and operator log/index mounts.

## Isolated smoke check

```powershell
.\.venv\Scripts\python.exe redteam/docker_smoke.py
```

The runner checks for a Linux engine, builds a uniquely tagged search image with a 15-minute build timeout, and starts a uniquely named container on a Docker-assigned loopback port. It uses a fresh token and no host mounts or model/cloud services. It checks health, UI, missing-token rejection, keyword excerpts, identity binding, a restricted finance query, disabled generation, recovery, and absence of installed model dependencies. It removes its container and image tag on exit; build cache can remain. Existing Compose services and volumes are not used.

Every run writes `.local-evaluations/docker-smoke-*/result.json`. Missing Docker or a stopped/non-Linux engine is `BLOCKED` with exit code 2; a failing check is not a pass. The API contract is also exercised against native real BM25 startup in `tests/test_docker_smoke.py`; that does not validate a container build.

## Optional generation image

Set `VAULTSEARCH_IMAGE_TARGET=full` and `VAULTSEARCH_SEARCH_ONLY=false` in `.env`, then run:

```powershell
docker compose --profile generation up --build
```

This installs the full model dependencies and may download model weights and build indexes. It has substantially higher memory and disk requirements. Full-image runtime, model usefulness, reranking and LocalStack remain unverified. Use the bounded evaluation guidance in `RUN_SECURITY.md` before measuring model behavior.
