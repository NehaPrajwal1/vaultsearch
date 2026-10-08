"""Start the actual search-only demo in the foreground. Never starts a model."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from app.acl import IdentityStore

ROOT = Path(__file__).resolve().parent


def prepare(user, port, root=ROOT):
    """Validate before starting; no existing server is stopped or reconfigured."""
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    identity = IdentityStore.load(root / "data/users_groups.json")
    user = user if user.startswith("user:") else "user:" + user
    if not identity.known_user(user):
        raise ValueError("Unknown demo identity. Run with --list-users to see valid personas.")
    if not (root / "data/chunks.json").is_file():
        raise ValueError("Missing data/chunks.json. Run ingestion/ingest.py first.")
    with socket.socket() as probe:
        # Exclusive bind detects another listener on Windows as well as Unix.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise ValueError(f"Port {port} is already occupied or unavailable. Stop your previous demo with Ctrl+C, or choose --port with another number. No server was stopped.") from exc
    token = secrets.token_urlsafe(32)
    return user, token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default="ines", help="Persona name or user:id, default ines")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--list-users", action="store_true")
    parser.add_argument("--check", action="store_true", help="Validate setup and free port without starting a server")
    args = parser.parse_args()
    try:
        if args.list_users:
            for record in IdentityStore.load(ROOT / "data/users_groups.json").directory():
                print(record["user_id"], "-", record["name"], "-", ", ".join(record["groups"]))
            return
        user, token = prepare(args.user, args.port)
        import uvicorn  # Fail with setup instructions before advertising a running demo.
        if args.check:
            print(f"Setup check passed for {user}; port {args.port} is free. No server or model started.")
            return
        env = dict(os.environ, VAULTSEARCH_USER=user, VAULTSEARCH_TOKEN=token, VAULTSEARCH_SEARCH_ONLY="true")
        print(f"Actual search-only demo: http://127.0.0.1:{args.port}/", flush=True)
        print(f"Identity: {user} | No AI model is loaded", flush=True)
        print(f"Demo token (paste into Connect): {token}", flush=True)
        print("Keep this terminal open. Ctrl+C stops the server. To switch users, stop and rerun with --user.", flush=True)
        subprocess.run([sys.executable, "-m", "uvicorn", "app.api:app", "--host", "127.0.0.1", "--port", str(args.port)], cwd=ROOT, env=env, check=True)
    except KeyboardInterrupt:
        print("Demo stopped.")
    except (ValueError, OSError, ImportError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Demo could not start: {exc}\nInstall requirements-search.txt with this Python interpreter if dependencies are missing.\n")


if __name__ == "__main__":
    main()
