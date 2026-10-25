"""Single-identity local demo boundary; not a production identity provider."""
import hmac
import hashlib
from pathlib import Path
import os

from fastapi import HTTPException, Request


def configure_identity(state, identity):
    user = os.getenv("VAULTSEARCH_USER", "")
    token = os.getenv("VAULTSEARCH_TOKEN", "")
    if not identity.known_user(user) or len(token) < 32:
        raise RuntimeError("Set a known VAULTSEARCH_USER and a random VAULTSEARCH_TOKEN of at least 32 characters")
    public_mode = os.getenv("VAULTSEARCH_PUBLIC_DEMO", "false").lower()
    if public_mode not in {"true", "false"}:
        raise RuntimeError("VAULTSEARCH_PUBLIC_DEMO must be true or false")
    state.public_demo = public_mode == "true"
    if state.public_demo:
        if user != "user:ines" or os.getenv("VAULTSEARCH_SEARCH_ONLY", "true").lower() != "true":
            raise RuntimeError("Public demo requires search-only mode and the Ines persona")
        # Pin the shipped synthetic fixture, preventing accidental publication of replacement data.
        root = Path(__file__).resolve().parent.parent
        fixtures = {
            "data/chunks.json": "e58f69c3d875da5bc3fe8122bb8fbde46cb1aac9",
            "data/users_groups.json": "16d9c6ae3f75bf076ad7ef811b77efc7aa6928de",
        }
        for name, expected in fixtures.items():
            raw = (root / name).read_bytes().replace(b"\r\n", b"\n")
            blob = b"blob " + str(len(raw)).encode() + b"\0" + raw
            if hashlib.sha1(blob).hexdigest() != expected:
                raise RuntimeError("Public demo requires the original synthetic dataset")
    state.demo_user = user
    state.demo_token = token


def trusted_user(request: Request) -> str:
    token = getattr(request.app.state, "demo_token", "")
    user = getattr(request.app.state, "demo_user", "")
    if getattr(request.app.state, "public_demo", False):
        if (request.method, request.url.path) not in {
            ("GET", "/api/users"), ("GET", "/api/directory"), ("POST", "/api/search")
        }:
            raise HTTPException(status_code=403, detail="Public demo supports evidence search only")
        return user
    supplied = request.headers.get("Authorization", "")
    if not token or not user or not hmac.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
        raise HTTPException(status_code=401, detail="Valid demo bearer token required", headers={"WWW-Authenticate": "Bearer"})
    return user


def check_claim(claim: str | None, user: str):
    if claim is not None and claim != user:
        raise HTTPException(status_code=403, detail="Identity is fixed by the server")
