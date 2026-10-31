"""CI-003 isolation, deterministic context integrity and cache measurement contracts."""
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from scripts import benchmark_buildx as b

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sha():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def test_context_uses_committed_bytes_and_only_declared_mutations(sha):
    original = dict(b.source_files(sha))
    base, manifest = b.inputs(sha, 'base')
    assert set(base) == set(original) | {'app/_build_version.txt'}
    pinned = b'@sha256:' in original['Dockerfile']
    assert {n for n in original if original[n] != base[n]} == (set() if pinned else {'Dockerfile'})
    assert base['app/_build_version.txt'] == sha.encode()
    assert b.inputs(sha, 'base') == (base, manifest)
    assert not manifest['release_image']
    assert manifest['original_dockerfile_sha256'] == b.sha256(original['Dockerfile'])
    for variant, changed in [('source', 'app/main.py'), ('dependencies', 'requirements.txt')]:
        files, metadata = b.inputs(sha, variant)
        assert {n for n in files if files[n] != base[n]} == {changed}
        assert metadata['manifest_sha256'] != manifest['manifest_sha256']
    assert not any(n.startswith(('.git/', '.env', 'local-data/', 'tests/', 'scripts/')) for n in base)


@pytest.mark.parametrize('sha', ['HEAD', 'a'*39, '../escape', 'A'*40])
def test_rejects_unidentified_source(sha):
    with pytest.raises(ValueError):
        b.inputs(sha, 'base')


def test_runtime_manifest_preserves_exact_source_and_excludes_tooling():
    compile(b.AUDIT, '<runtime-audit>', 'exec')
    manifest = {'files': {'app/main.py':'source-hash', 'requirements.txt':'requirements-hash',
                         'frontend/package.json':'build-only'}, 'builder_images':['pinned-node']}
    compiled = {'app/spa_dist/index.html':'index-hash', 'app/spa_dist/assets/index-abcdefgh.js':'js-hash'}
    files = {'app/main.py':'source-hash', 'requirements.txt':'requirements-hash'} | compiled
    b.validate_runtime_files(manifest, {'files':files, 'compiled':compiled})
    for changed in (files | {'frontend/package.json':'build-only'}, files | {'app/node_modules/tool.js':'tool'},
                    files | {'app/main.py':'altered'}, {'app/main.py':'source-hash'}):
        with pytest.raises(ValueError): b.validate_runtime_files(manifest, {'files':changed, 'compiled':compiled})
    with pytest.raises(ValueError): b.validate_runtime_files(manifest, {'files':files, 'compiled':{}})


def test_trial_salt_is_shared_by_methods_but_invalidates_prior_dependency_cache(sha):
    first, first_meta = b.inputs(sha, 'base', 'trial-1')
    again, _ = b.inputs(sha, 'base', 'trial-1')
    source, source_meta = b.inputs(sha, 'source', 'trial-1')
    dependencies, dependency_meta = b.inputs(sha, 'dependencies', 'trial-1')
    second, second_meta = b.inputs(sha, 'base', 'trial-2')
    assert first == again
    assert first['requirements.txt'] == source['requirements.txt']
    assert first_meta['requirements_sha256'] == source_meta['requirements_sha256']
    assert dependency_meta['requirements_sha256'] != first_meta['requirements_sha256']
    assert second_meta['requirements_sha256'] != first_meta['requirements_sha256']
    assert {n for n in first if first[n] != second[n]} == {'requirements.txt'}
    installed = lambda data: [line for line in data.decode().splitlines() if line and not line.startswith('#')]
    assert installed(first['requirements.txt']) == installed(second['requirements.txt'])
    assert installed(dependencies['requirements.txt']) == installed(first['requirements.txt']) + ['six==1.17.0']


def test_progress_preserves_cache_hits_and_transfer_spans():
    items = [dict(id='pip', name='[4/6] RUN pip install -r requirements.txt',
                  started='2026-10-29T10:00:00Z', completed='2026-10-29T10:00:02Z', cached=True),
             dict(id='import', name='importing cache manifest from local',
                  started='2026-10-29T10:00:00Z', completed='2026-10-29T10:00:01Z'),
             dict(id='export', name='exporting cache to client directory',
                  started='2026-10-29T10:00:02Z', completed='2026-10-29T10:00:05Z')]
    parsed = b.parse_progress('\n'.join(json.dumps(i) for i in items))
    assert parsed['dependency_cached'] is True
    assert parsed['dependency_seconds'] == 2
    assert parsed['cache_import_seconds'] == 1
    assert parsed['cache_export_seconds'] == 3
    assert parsed['cache_transfer_span_seconds'] == 4
    assert b.parse_progress('not json')['cache_import_seconds'] is None
    wrapped = '\n'.join(json.dumps({'vertexes': [dict(i, digest=i['id'])]}) for i in items)
    assert b.parse_progress(wrapped)['dependency_seconds'] == 2
    assert b.parse_progress(wrapped)['cache_transfer_span_seconds'] == 4


def test_summary_uses_medians_and_rejects_false_invalidation_evidence(tmp_path):
    report = {'repeats': 2, 'source_sha': 'a'*40, 'session': 'unit', 'runs': [],
              'setup_seconds': [], 'cleanup_errors': []}
    for mode in ('no-cache', 'docker-cache', 'buildx-internal', 'buildx-local'):
        for scenario in b.SCENARIOS:
            for repeat in range(2):
                hit = mode != 'no-cache' and scenario in ('warm', 'source')
                record = {'mode': mode, 'scenario': scenario, 'repeat': repeat,
                          'seconds': 1 + 2*repeat, 'success': True,
                          'smoke': {'status': 'PASS', 'rootfs_diffids': ['base']*4,
                                    'size_bytes': 100}}
                report['runs'].append(record)
                (tmp_path/f'{mode}-{repeat}-{scenario}.jsonl').write_text(json.dumps(
                    {'id': 'pip', 'name': 'RUN pip install', 'cached': hit,
                     'started': '2026-10-29T10:00:00Z', 'completed': '2026-10-29T10:00:01Z'}))
    b.write_json(tmp_path/'results.json', report)
    summary = b.summarize(tmp_path)
    assert all(row['seconds'] == 2 for row in summary['rows'])
    assert all(row['cache_import_seconds'] is None for row in summary['rows'])
    poisoned = tmp_path/'docker-cache-0-dependencies.jsonl'
    vertex = json.loads(poisoned.read_text())
    vertex['cached'] = True
    poisoned.write_text(json.dumps(vertex))
    with pytest.raises(AssertionError):
        b.summarize(tmp_path)


def test_integration_excludes_automatic_experiment_and_keeps_production_builder():
    assert not (ROOT/'.github/workflows/buildx-benchmark.yml').exists()
    for path in (ROOT/'.github/workflows').glob('*.yml'):
        text = path.read_text()
        wf = yaml.load(text, Loader=yaml.BaseLoader)
        assert 'pull_request_target' not in wf['on']
        assert 'ci/ci-003-buildx-benchmark' not in text
        assert not any(action in text for action in ('docker/build-push-action@', 'docker/setup-buildx-action@', 'type=registry'))


@pytest.mark.parametrize('recipe', [
    (ROOT/'Dockerfile').read_bytes(),
    b'FROM python:3.12-slim@sha256:' + b'a'*64 + b'\nCOPY app /app\n'])
def test_committed_pin_is_preserved_exactly_with_or_without_leading_comments(monkeypatch,sha,recipe):
    source = dict(b.source_files(sha));source['Dockerfile'] = recipe
    # This fixture intentionally swaps in a working recipe before its commit;
    # supply its exact working input set as well. Release builds still use Git.
    from scripts.gcp.frontend_build import MARKER, is_frontend_input
    if MARKER in recipe:
        source.update({p.relative_to(ROOT).as_posix():p.read_bytes()
                       for p in (ROOT/'frontend').rglob('*')
                       if p.is_file() and is_frontend_input(p.relative_to(ROOT).as_posix())})
    monkeypatch.setattr(b,'source_files',lambda _:source.items())
    files, manifest = b.inputs(sha,'base')
    assert files['Dockerfile'] == recipe
    assert manifest['dockerfile_sha256'] == manifest['original_dockerfile_sha256']
    assert manifest['base_image'] == [line[5:] for line in recipe.decode().splitlines() if line.startswith('FROM ')][-1]


@pytest.mark.parametrize('recipe', [b'FROM python:3.13-slim', b'FROM example/other@sha256:' + b'a'*64,
    b'FROM python:3.12-slim\nFROM python:3.12-slim', b'FROM python:3.12-slim@sha256:invalid'])
def test_unreviewed_recipe_is_rejected_instead_of_stripping_or_replacing_pin(monkeypatch,sha,recipe):
    source = dict(b.source_files(sha));source['Dockerfile'] = recipe
    monkeypatch.setattr(b,'source_files',lambda _:source.items())
    with pytest.raises(ValueError,match='Review benchmark'):b.inputs(sha,'base')
