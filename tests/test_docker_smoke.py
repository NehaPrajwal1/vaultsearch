"""Check the smoke contract using native real BM25 startup, with no model."""
import pytest
from fastapi.testclient import TestClient

from app.api import app
from redteam.docker_smoke import check_api


@pytest.fixture
def search_client(monkeypatch):
    token = 'correct-test-token-with-at-least-32-characters'
    monkeypatch.setenv('VAULTSEARCH_USER', 'user:ines')
    monkeypatch.setenv('VAULTSEARCH_TOKEN', token)
    monkeypatch.setenv('VAULTSEARCH_SEARCH_ONLY', 'true')
    monkeypatch.delenv('AUDIT_DYNAMODB_TABLE', raising=False)
    with TestClient(app) as client:
        yield client, token


def test_smoke_contract_against_real_keyword_api(search_client):
    client, token = search_client
    checks = check_api(client, token)
    assert checks['restricted_budget_absent'] and checks['search_recovers']


def test_smoke_contract_rejects_a_wrong_deployment_token(search_client):
    client, _ = search_client
    with pytest.raises(RuntimeError, match='Authorized keyword search failed'):
        check_api(client, 'wrong-token')


@pytest.mark.parametrize('mode,image_mode,message', [
    ('maybe', 'search', 'must be true or false'),
    ('false', 'search', 'VAULTSEARCH_IMAGE_TARGET=full'),
    ('FALSE', 'search', 'VAULTSEARCH_IMAGE_TARGET=full'),
])
def test_entrypoint_rejects_bad_mode_before_corpus_or_index_work(tmp_path, mode, image_mode, message):
    import os
    from pathlib import Path
    import shutil
    import subprocess

    shell = shutil.which('bash')
    git = shutil.which('git')
    if not shell and git:
        candidate = Path(git).resolve().parent.parent / 'bin' / 'bash.exe'
        if candidate.is_file():
            shell = str(candidate)
    if not shell:
        pytest.skip('POSIX shell not available for container entrypoint check')
    entry = Path(__file__).resolve().parent.parent / 'docker-entrypoint.sh'
    result = subprocess.run([shell, str(entry)], cwd=tmp_path, text=True, capture_output=True,
                            env=dict(os.environ, VAULTSEARCH_SEARCH_ONLY=mode,
                                     VAULTSEARCH_IMAGE_MODE=image_mode), timeout=10)
    assert result.returncode == 2
    assert message in result.stderr
    assert not list(tmp_path.iterdir())
