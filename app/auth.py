"""Single-identity local demo boundary; not a production identity provider."""
import hmac
import os

from fastapi import HTTPException, Request


def configure_identity(state, identity):
    user = os.getenv("VAULTSEARCH_USER", "")
    token = os.getenv("VAULTSEARCH_TOKEN", "")
    if not identity.known_user(user) or len(token) < 32:
        raise RuntimeError("Set a known VAULTSEARCH_USER and a random VAULTSEARCH_TOKEN of at least 32 characters")
    state.demo_user = user
    state.demo_token = token


def trusted_user(request: Request) -> str:
    token = getattr(request.app.state, "demo_token", "")
    user = getattr(request.app.state, "demo_user", "")
    supplied = request.headers.get("Authorization", "")
    if not token or not user or not hmac.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
        raise HTTPException(status_code=401, detail="Valid demo bearer token required", headers={"WWW-Authenticate": "Bearer"})
    return user


def check_claim(claim: str | None, user: str):
    if claim is not None and claim != user:
        raise HTTPException(status_code=403, detail="Identity is fixed by the server")
