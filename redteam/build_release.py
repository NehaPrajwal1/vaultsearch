"""Build and validate a curated local source ZIP. No upload or Git mutation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Explicit reviewed source selection. Runtime logs, credentials and history are excluded.
SELECTED = ['.dockerignore', '.env.example', '.gitattributes', '.github/workflows/ci.yml', '.gitignore', 'DESIGN.md', 'Dockerfile', 'README.md', 'RUN_SECURITY.md', 'START_HERE.md', 'app/__init__.py', 'app/acl.py', 'app/agents.py', 'app/api.py', 'app/auth.py', 'app/cloud_audit.py', 'app/ollama_client.py', 'app/presentation.py', 'app/retrieval_core.py', 'app/schema.py', 'app/tools.py', 'cloud/ingest_worker.py', 'cloud/main.tf', 'cloud/requirements.txt', 'cloud/sync_sources.py', 'data/chunks.json', 'data/sources/drive.json', 'data/sources/injections.json', 'data/sources/slack.json', 'data/sources/tickets.json', 'data/users_groups.json', 'docker-compose.yml', 'docker-entrypoint.sh', 'docs/architecture.md', 'docs/case-study.md', 'docs/demo.md', 'docs/docker.md', 'docs/reference.md', 'docs/validation.md', 'eval/evaluate.py', 'eval/scale_study.py', 'indexing/build_indexes.py', 'ingestion/generate_data.py', 'ingestion/ingest.py', 'mcp_server.py', 'redteam/README.md', 'redteam/api_probe.py', 'redteam/build_colab_bundle.py', 'redteam/build_release.py', 'redteam/docker_smoke.py', 'redteam/focused_probe.py', 'redteam/mcp_smoke.py', 'redteam/presentation_probe.py', 'redteam/release_check.py', 'redteam/resume_redteam.py', 'redteam/retrieval_probe.py', 'redteam/run_redteam.py', 'reports/portfolio_evidence.json', 'reports/release_review.md', 'reports/release_validation.json', 'requirements-search.txt', 'requirements-test.txt', 'requirements.txt', 'run_demo.py', 'setup.sh', 'tests/fixtures/release_acceptance.json', 'tests/scripted_ui_server.py', 'tests/test_acl.py', 'tests/test_agent_loop.py', 'tests/test_api_probe.py', 'tests/test_demo_launcher.py', 'tests/test_docker_smoke.py', 'tests/test_evidence_boundary.py', 'tests/test_identity_boundary.py', 'tests/test_ingestion.py', 'tests/test_integration_retrieval.py', 'tests/test_presentation.py', 'tests/test_redteam.py', 'tests/test_release.py', 'tests/test_resume_redteam.py', 'tests/test_retrieval_primitives.py', 'tests/test_tools.py', 'tests/test_verification.py', 'web/app.js', 'web/index.html', 'web/style.css']


def main():
    from redteam.api_probe import source_provenance
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / '.local-evaluations' / ('release-package-' + stamp)
    out.mkdir(parents=True)
    contents = {name: (ROOT / name).read_bytes() for name in SELECTED}
    example = contents['.env.example'].decode('utf-8')
    if re.search(r'^VAULTSEARCH_TOKEN=\S+', example, re.M):
        raise ValueError('The environment example must not contain an operator token')
    adjustments = []
    # Historical local references can point outside the deliberately curated snapshot.
    for name in list(contents):
        if not name.endswith('.md'):
            continue
        def link(match):
            label, target = match.groups()
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                return match.group(0)
            relative = target.split('#', 1)[0].strip('<>')
            resolved = (ROOT / Path(name).parent / relative).resolve()
            if resolved.is_relative_to(ROOT) and resolved.relative_to(ROOT).as_posix() in contents:
                return match.group(0)
            adjustments.append({'file': name, 'omitted_reference': target})
            return label + ' (historical local reference; omitted from this snapshot)'
        contents[name] = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link,
                                contents[name].decode('utf-8')).encode('utf-8')
    for name in contents:
        # Every allowlisted artifact is UTF-8 source/data, not an arbitrary binary.
        normalized = contents[name].decode('utf-8').replace('\r\n', '\n').encode('utf-8')
        if normalized != contents[name]:
            adjustments.append({'file': name, 'normalization': 'UTF-8 text with LF line endings'})
        contents[name] = normalized
    provenance = source_provenance(ROOT)
    manifest = {
        'created_utc': stamp, 'commit': provenance['commit'],
        'working_tree_dirty': provenance['working_tree_dirty'],
        'scope': 'Local synthetic search demo; optional model/cloud features remain experimental',
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(contents.items())},
        'source_files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                         for name in SELECTED},
        'packaging_adjustments': adjustments,
    }
    contents['BUNDLE_MANIFEST.json'] = json.dumps(manifest, indent=2).encode('utf-8')
    archive = out / 'VaultSearch-source.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(contents.items()):
            z.writestr(name, data)
    extracted = out / 'verified-source'
    extracted.mkdir()
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if not (extracted / member.filename).resolve().is_relative_to(extracted.resolve()):
                raise ValueError('Unsafe package path')
        z.extractall(extracted)
    verified = source_provenance(extracted)
    result = {'status': 'INCOMPLETE', 'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'files': len(contents), 'provenance': verified,
              'runtime': 'existing dependency environment; extracted source with no Git or private reports'}
    result_path = out / 'package-validation.json'
    result_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    try:
        check = subprocess.run([sys.executable, 'redteam/release_check.py'], cwd=extracted,
                               capture_output=True, text=True, timeout=180)
        result.update(returncode=check.returncode, stdout=check.stdout, stderr=check.stderr,
                      status='PASSED' if check.returncode == 0 else 'FAILED')
    except subprocess.TimeoutExpired as exc:
        result.update(status='INCOMPLETE', reason='180-second validation deadline',
                      stdout=(exc.stdout or b'').decode('utf-8', errors='replace')
                      if isinstance(exc.stdout, bytes) else exc.stdout)
    finally:
        result_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result['status'], archive)
    print(result.get('stdout', ''), result.get('stderr', ''))
    if result['status'] != 'PASSED':
        raise RuntimeError('Extracted package validation did not pass')


if __name__ == '__main__':
    main()
