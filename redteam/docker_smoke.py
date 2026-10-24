"""Bounded Docker search-image checks; never starts a model or cloud service."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
import uuid

import httpx

ROOT = Path(__file__).resolve().parent.parent


def check_api(client, token):
    """Exercise the same API contract against a container or native test server."""
    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    health = client.get('/health')
    require(health.status_code == 200 and health.json().get('search_only') is True,
            'Not a healthy search-only server')
    require(client.get('/').status_code == 200, 'Web UI unavailable')
    query = {'query': 'paid time off'}
    require(client.post('/api/search', json=query).status_code == 401,
            'Search accepted missing credentials')
    headers = {'Authorization': 'Bearer ' + token}
    search = client.post('/api/search', json=query, headers=headers)
    require(search.status_code == 200, 'Authorized keyword search failed')
    rows = search.json().get('modes', {}).get('bm25', {}).get('results', [])
    require(bool(rows) and all(row.get('text') and row.get('chunk_id') for row in rows),
            'Keyword search did not return complete source excerpts')
    users = client.get('/api/users', headers=headers)
    require(users.status_code == 200 and
            [row['user_id'] for row in users.json()['users']] == ['user:ines'],
            'Server identity differs from the configured persona')
    conflict = client.post('/api/search', json={**query, 'user_id': 'user:dmitri'}, headers=headers)
    require(conflict.status_code == 403, 'Client identity override was accepted')
    budget = client.post('/api/search', json={'query': 'Q3 infrastructure budget'}, headers=headers)
    require(budget.status_code == 200 and '1.2 million' not in budget.text and
            '1,200,000' not in budget.text, 'Restricted finance evidence was disclosed')
    disabled = client.post('/api/ask', json={'question': 'paid time off'}, headers=headers)
    require(disabled.status_code == 409, 'Generation was not disabled')
    recovery = client.post('/api/search', json=query, headers=headers)
    require(recovery.status_code == 200 and
            recovery.json()['modes']['bm25']['results'], 'Search did not recover after errors')
    return {'health': 200, 'ui': 200, 'missing_token': 401, 'search': 200,
            'identity_conflict': 403, 'restricted_budget_absent': True,
            'generation_disabled': 409, 'search_recovers': True, 'excerpts': len(rows)}


def main():
    out = ROOT / '.local-evaluations' / ('docker-smoke-' +
            datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True)
    report = {'status': 'INCOMPLETE', 'scope': 'Docker search target only; no model or LocalStack',
              'checks': {}, 'cleanup': {}}
    source = [ROOT / name for name in ('.gitattributes', '.dockerignore', 'Dockerfile',
              'docker-compose.yml', 'docker-entrypoint.sh', 'requirements-search.txt',
              'requirements.txt', 'redteam/docker_smoke.py', 'data/chunks.json', 'data/users_groups.json')]
    source += [p for folder in ('app', 'web', 'ingestion') for p in (ROOT / folder).rglob('*')
               if p.is_file() and p.suffix in {'.py', '.js', '.html', '.css', '.json'}]
    report['source'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(source)}
    suffix = uuid.uuid4().hex[:12]
    name, image = 'vaultsearch-smoke-' + suffix, 'vaultsearch-smoke:' + suffix
    docker = shutil.which('docker')
    built = started = False

    def command(args, timeout=30, env=None):
        return subprocess.run([docker, *args], cwd=ROOT, text=True,
                              capture_output=True, timeout=timeout, env=env)

    def checked(args, timeout=30, env=None):
        result = command(args, timeout, env)
        if result.returncode:
            raise RuntimeError(result.stderr[-4000:] or result.stdout[-4000:] or 'Docker command failed')
        return result.stdout.strip()

    try:
        if not docker:
            report.update(status='BLOCKED', reason='Docker CLI is not installed or is not on PATH')
        else:
            engine = command(['info', '--format', '{{.OSType}}'])
            if engine.returncode or engine.stdout.strip() != 'linux':
                report.update(status='BLOCKED', reason='A running Linux Docker engine is required')
            else:
                report['checks']['engine'] = 'linux'
                checked(['build', '--target', 'search', '--tag', image, '.'], timeout=900)
                built = True
                token = secrets.token_urlsafe(32)
                # Docker reads the token from the process environment, not argv or a file.
                env = dict(os.environ, VAULTSEARCH_TOKEN=token)
                started = True  # Cleanup also covers a partially successful docker run.
                checked(['run', '--detach', '--name', name, '--publish', '127.0.0.1::8000',
                         '--env', 'VAULTSEARCH_USER=user:ines', '--env', 'VAULTSEARCH_TOKEN',
                         '--env', 'VAULTSEARCH_SEARCH_ONLY=true', image], env=env)
                address = checked(['port', name, '8000/tcp']).splitlines()[0]
                if not address.startswith('127.0.0.1:'):
                    raise RuntimeError('Unexpected container port binding')
                with httpx.Client(base_url='http://' + address, timeout=3, trust_env=False) as client:
                    deadline = time.monotonic() + 45
                    while True:
                        try:
                            if client.get('/health').status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Container did not become ready within 45 seconds')
                        time.sleep(.25)
                    report['checks']['api'] = check_api(client, token)
                probe = "import importlib.util,json; print(json.dumps({m:importlib.util.find_spec(m) is not None for m in ['torch','sentence_transformers','faiss']}))"
                modules = json.loads(checked(['exec', name, 'python', '-c', probe]))
                if any(modules.values()):
                    raise RuntimeError('Search image unexpectedly includes model dependencies')
                report['checks']['model_dependencies_installed'] = modules
                report['status'] = 'PASSED'
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, IndexError, httpx.HTTPError) as exc:
        report.update(status='FAILED', reason=str(exc))
    finally:
        for needed, key, args in ((started, 'container', ['rm', '--force', name]),
                                  (built, 'image', ['image', 'rm', image])):
            if needed:
                try:
                    report['cleanup'][key] = command(args).returncode == 0
                except (OSError, subprocess.TimeoutExpired):
                    report['cleanup'][key] = False
        if report['status'] == 'PASSED' and not all(report['cleanup'].values()):
            report['status'] = 'FAILED_CLEANUP'
        (out / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(report['status'] + ': ' + str(out / 'result.json'))
    return 0 if report['status'] == 'PASSED' else 2 if report['status'] == 'BLOCKED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
