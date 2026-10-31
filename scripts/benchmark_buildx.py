"""CI-003 local QA only. Never calls the production builder or publishes an image.

python -m scripts.benchmark_buildx run --sha <commit> --repeats 3
python -m scripts.benchmark_buildx prepare --sha <commit> --output <new-dir>
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import statistics
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from scripts.gcp.deployment import source_files

ROOT = Path(__file__).resolve().parents[1]
BASE = 'python:3.12-slim@sha256:1148dbb014615300fa7e713b2f94f550c0d1c69780c0805f84f093ceee34dd0b'
BUILDKIT = 'moby/buildkit:v0.31.1@sha256:2caaaf9bc673a82d5b0a87824f8375e6b2b36b55001dad611230516c724e9fba'
SCENARIOS = ('cold', 'warm', 'source', 'dependencies')


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def inputs(sha, variant, trial=None):
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('Use a full committed SHA')
    if variant not in ('base', 'source', 'dependencies'):
        raise ValueError('Unknown synthetic variant')
    files = dict(source_files(sha))
    original = sha256(files['Dockerfile'])
    # Preserve committed pins byte-for-byte, including the CI-002 index pin.
    # Only historical floating-input benchmarks get the original QA-only freeze.
    recipe = files['Dockerfile'].decode()
    instructions = [line.strip() for line in recipe.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    froms = [line for line in instructions if line.startswith('FROM ')]
    from scripts.gcp.frontend_build import MARKER, validate_frontend_source
    integrated = MARKER in files['Dockerfile']
    if integrated:
        validate_frontend_source(files)
    elif len(froms) != 1 or instructions[0] != froms[0] or not re.fullmatch(r'FROM python:3\.12-slim(?:@sha256:[a-f0-9]{64})?', froms[0]):
        raise ValueError('Review benchmark base selection for this Dockerfile first')
    declared_base = froms[-1][5:]
    base_image = declared_base if '@sha256:' in declared_base else BASE
    if declared_base != base_image:
        files['Dockerfile'] = recipe.replace('FROM ' + declared_base, 'FROM ' + base_image, 1).encode()
    files['app/_build_version.txt'] = sha.encode()
    if trial is not None:
        if not re.fullmatch('[a-z0-9-]+', trial):
            raise ValueError('Invalid trial identifier')
        # Per-trial comment changes the COPY key, not installed requirements.
        # It prevents prior trials/user cache from satisfying dependency rebuilds.
        files['requirements.txt'] += ('\n# CI-003 isolated trial ' + trial + '\n').encode()
    if variant == 'source':
        files['app/main.py'] += b'\n# CI-003 deterministic synthetic invalidation v1\n'
    if variant == 'dependencies':
        files['requirements.txt'] += b'\n# CI-003 synthetic additional dependency\nsix==1.17.0\n'
    manifest = {name: sha256(data) for name, data in sorted(files.items())}
    return files, {'source_sha': sha, 'synthetic_variant': variant, 'trial': trial,
                   'release_image': False, 'original_dockerfile_sha256': original,
                   'dockerfile_sha256': manifest['Dockerfile'],
                   'requirements_sha256': manifest['requirements.txt'],
                   'base_image': base_image, 'builder_images': froms[:-1], 'platform': 'linux/amd64', 'files': manifest,
                   'manifest_sha256': sha256(json.dumps(manifest, sort_keys=True).encode())}


def prepare(sha, output, trial=None):
    output.mkdir(parents=True, exist_ok=False)
    manifests = {}
    for variant in ('base', 'source', 'dependencies'):
        files, manifests[variant] = inputs(sha, variant, trial)
        for name, data in files.items():
            target = output / variant / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    write_json(output / 'inputs.json', manifests)
    return manifests


def parse_progress(log):
    """BuildKit rawjson vertices: durations are work spans, not extra wall time."""
    vertices = {}
    for line in log.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        # docker build wraps SolveStatus.vertexes; buildx emits flat vertices.
        for vertex in item.get('vertexes', [item]):
            key = vertex.get('id', vertex.get('digest'))
            if key and 'name' in vertex:
                vertices.setdefault(key, {}).update(vertex)
    def duration(vertex):
        if not vertex.get('started') or not vertex.get('completed'):
            return None
        return (datetime.fromisoformat(vertex['completed'].replace('Z', '+00:00')) -
                datetime.fromisoformat(vertex['started'].replace('Z', '+00:00'))).total_seconds()
    def select(text):
        return [v for v in vertices.values() if text in v['name']]
    def total(items):
        values = [duration(v) for v in items]
        return round(sum(v for v in values if v is not None), 6) if values else None
    dep = select('RUN pip install')
    imports, exports = select('importing cache'), select('exporting cache')
    return {'dependency_seconds': total(dep),
            'dependency_cached': all(v.get('cached', False) for v in dep) if dep else None,
            'cache_import_seconds': total(imports), 'cache_export_seconds': total(exports),
            'cache_transfer_span_seconds': total(imports + exports),
            'cached_vertices': [v['name'] for v in vertices.values() if v.get('cached')],
            'vertices': list(vertices.values())}


AUDIT = r'''
import hashlib, importlib.util, json, pathlib, re, shutil, sys
from importlib.metadata import version
assert sys.version_info[:2] == (3, 12)
for module in ('pytest', 'playwright', 'pypdf', 'fitz'):
    assert importlib.util.find_spec(module) is None
import app.main, app.worker
root=pathlib.Path('/app')
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
assert not any(p in files for p in ['.env', 'data/tripse.sqlite3'])
assert list((root/'demo-fixtures/gt-v1').rglob('*.json'))
for line in (root/'requirements.txt').read_text().splitlines():
    if '==' in line and not line.startswith('#'):
        name, expected=line.split('=='); assert version(name.split('[')[0]) == expected
compiled={n:h for n,h in files.items() if n.startswith('app/spa_dist/')}
if compiled:
    assert not shutil.which('node') and not shutil.which('npm')
    assert not list(root.rglob('node_modules'))
    html=(root/'app/spa_dist/index.html').read_text()
    assert html.count('__TRIPSE_STYLE_NONCE__') == 1
    refs=re.findall(r'(?:src|href)="(/app/assets/[^\"]+)"', html)
    expected={'app/spa_dist/index.html'} | {'app/spa_dist/'+p.removeprefix('/app/') for p in refs}
    assert refs and set(compiled)==expected
    assert any(p.endswith('.js') for p in refs) and any(p.endswith('.css') for p in refs)
    assert all(re.fullmatch(r'/app/assets/[\w.-]+-[\w-]{8,}\.(js|css)', p) for p in refs)
print(json.dumps({'python':sys.version, 'files':files, 'compiled':compiled}))
'''


def validate_runtime_files(manifest, audit):
    expected = {n: h for n, h in manifest['files'].items()
                if n.startswith(('app/', 'demo-fixtures/')) or n == 'requirements.txt'}
    compiled = audit.get('compiled', {})
    if bool(manifest.get('builder_images')) != bool(compiled):
        raise ValueError('Benchmark runtime lacks the expected compiled output')
    if any(n != 'app/spa_dist/index.html' and not re.fullmatch(r'app/spa_dist/assets/[\w.-]+-[\w-]{8,}\.(js|css)', n) for n in compiled):
        raise ValueError('Unexpected generated runtime path')
    if audit['files'] != expected | compiled:
        raise ValueError('Image content differs from allowlisted QA inputs/output')


def smoke(tag, manifest, logdir):
    info = json.loads(command('docker', 'image', 'inspect', tag))[0]
    assert info['Os'] == 'linux' and info['Architecture'] == 'amd64'
    assert info['Config']['Cmd'] == ['python', '-m', 'uvicorn', 'app.main:app', '--host',
                                   '0.0.0.0', '--port', '8000', '--no-access-log',
                                   '--timeout-graceful-shutdown', '8']
    audit = json.loads(command('docker', 'run', '--rm', '--network', 'none', tag, 'python', '-c', AUDIT))
    # Compiled assets are generated by the pinned stage, not copied source files.
    # AUDIT validates their closed index/hashed-asset tree separately; source files
    # still require exact manifest equality. This manual QA is not release proof.
    validate_runtime_files(manifest, audit)
    cid = command('docker', 'run', '-d', '--read-only', '--tmpfs', '/tmp', '--cap-drop=ALL',
                  '--pids-limit=128', '-p', '127.0.0.1::8000',
                  '-e', 'APP_ENV=dev', '-e', 'K_SERVICE=tripse-ai-dev',
                  '-e', 'PLANNING_MODE=mock', '-e', 'CLOUD_FEATURE_MODE=readonly_demo',
                  '-e', 'EXPECTED_IMAGE_SHA=' + manifest['source_sha'], tag)
    try:
        base = 'http://' + command('docker', 'port', cid, '8000/tcp')
        for _ in range(100):
            try:
                with urlopen(base + '/health', timeout=1) as response:
                    health = json.load(response)
                assert health['image_version'] == manifest['source_sha']
                break
            except (URLError, ConnectionError):
                time.sleep(.1)
        else:
            raise RuntimeError('Benchmark image readiness timeout')
        with urlopen(base + '/preview/documents/collection', timeout=5) as response:
            assert response.status == 200
        command('docker', 'stop', '--time=10', cid)
        assert command('docker', 'inspect', '--format', '{{.State.ExitCode}}', cid) == '0'
        return {'status': 'PASS', 'python': audit['python'], 'size_bytes': info['Size'],
                'rootfs_diffids': info['RootFS']['Layers'], 'image_id': info['Id'],
                'entrypoint': info['Config']['Cmd'], 'health': health,
                'verified_files': len(expected)}
    finally:
        try:
            (logdir / (tag.split(':')[-1] + '-runtime.log')).write_text(
                command('docker', 'logs', cid), encoding='utf-8')
        finally:
            command('docker', 'rm', '-f', cid)


def benchmark(sha, output, repeats):
    output.mkdir(parents=True, exist_ok=False)
    manifests = {}
    context_root = output
    session = uuid4().hex[:10]
    builders, tags = set(), set()
    report = {'session': session, 'source_sha': sha, 'release_image': False,
              'host': platform.platform(), 'repeats': repeats, 'runs': [],
              'docker': json.loads(command('docker', 'version', '--format', '{{json .}}')),
              'resources': json.loads(command('docker', 'info', '--format',
                                            '{"cpus":{{.NCPU}},"memory":{{.MemTotal}}}')),
              'buildx': command('docker', 'buildx', 'version'), 'buildkit_image': BUILDKIT,
              'default_builder': command('docker', 'buildx', 'inspect'), 'setup_seconds': []}
    def save():
        write_json(output / 'results.json', report)
    def builder(suffix):
        name = 'tripse-ci003-' + session + '-' + suffix
        started = time.perf_counter()
        command('docker', 'buildx', 'create', '--name', name, '--driver', 'docker-container',
                '--driver-opt', 'image=' + BUILDKIT)
        builders.add(name)
        details = command('docker', 'buildx', 'inspect', '--bootstrap', name)
        report['setup_seconds'].append({'builder': name, 'seconds': time.perf_counter()-started,
                                        'details': details})
        return name
    def remove_builder(name):
        command('docker', 'buildx', 'rm', name)
        builders.remove(name)
    def build(mode, scenario, rep, name=None, cache=None, export=None, no_cache=False):
        variant = scenario if scenario in ('source', 'dependencies') else 'base'
        tag = f'tripse-ci003-qa:{session}-{mode}-{rep}-{scenario}'
        tags.add(tag)
        args = ['docker', 'build'] if mode in ('no-cache', 'docker-cache') else ['docker', 'buildx', 'build', '--builder', name, '--load']
        args += ['--platform=linux/amd64', '--progress=rawjson', '-t', tag]
        if no_cache:
            args += ['--no-cache']
        if cache:
            args += ['--cache-from', 'type=local,src=' + str(cache)]
        if export:
            args += ['--cache-to', 'type=local,mode=max,dest=' + str(export)]
        args += [str(context_root / variant)]
        started = time.perf_counter()
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        elapsed = time.perf_counter() - started
        raw = result.stderr + '\n' + result.stdout
        (output / f'{mode}-{rep}-{scenario}.jsonl').write_text(raw, encoding='utf-8')
        record = {'mode': mode, 'scenario': scenario, 'repeat': rep, 'seconds': elapsed,
                  'success': result.returncode == 0, 'command': args, **parse_progress(raw)}
        report['runs'].append(record)
        save()
        if result.returncode:
            raise RuntimeError(f'{mode}/{scenario}: inspect retained build log')
        record['smoke'] = smoke(tag, manifests[variant], output)
        save()
        print(f'{mode}/{rep}/{scenario}: {elapsed:.3f}s PASS', flush=True)
    try:
        for rep in range(repeats):
            context_root = output / f'trial-{rep}'
            manifests = prepare(sha, context_root, f'{session}-{rep}')
            # Force first build cold; do not prune the user's shared Docker builder.
            # Run cache scenarios BEFORE no-cache variants populate their COPY keys.
            for scenario in SCENARIOS:
                build('docker-cache', scenario, rep, no_cache=scenario == 'cold')
            for scenario in SCENARIOS:
                build('no-cache', scenario, rep, no_cache=True)
            internal = builder(f'internal-{rep}')
            for scenario in SCENARIOS:
                build('buildx-internal', scenario, rep, internal)
            remove_builder(internal)
            seed = output / f'cache-{rep}'
            for scenario in SCENARIOS:
                # A fresh daemon for every import rules out internal-cache false hits.
                fresh = builder(f'external-{rep}-{scenario}')
                build('buildx-local', scenario, rep, fresh,
                      cache=None if scenario == 'cold' else seed,
                      export=seed if scenario == 'cold' else output / f'cache-{rep}-{scenario}')
                remove_builder(fresh)
        report['medians'] = {mode: {scenario: statistics.median(
            r['seconds'] for r in report['runs'] if r['mode'] == mode and r['scenario'] == scenario)
            for scenario in SCENARIOS} for mode in ('no-cache', 'docker-cache', 'buildx-internal', 'buildx-local')}
    finally:
        report['cleanup_errors'] = []
        for name in sorted(builders):
            try:
                command('docker', 'buildx', 'rm', name)
            except subprocess.CalledProcessError as error:
                report['cleanup_errors'].append(str(error))
        for tag in sorted(tags):
            result = subprocess.run(['docker', 'image', 'rm', tag], capture_output=True, text=True)
            if result.returncode:
                report['cleanup_errors'].append(result.stderr)
        save()


def summarize(output):
    """Reparse retained logs and refuse incomplete or invalid cache experiments."""
    report = json.loads((output / 'results.json').read_text(encoding='utf-8'))
    modes = ('no-cache', 'docker-cache', 'buildx-internal', 'buildx-local')
    assert len(report['runs']) == report['repeats'] * len(modes) * len(SCENARIOS)
    rows = []
    for run in report['runs']:
        assert run['success'] and run['smoke']['status'] == 'PASS'
        log = output / f"{run['mode']}-{run['repeat']}-{run['scenario']}.jsonl"
        run.update(parse_progress(log.read_text(encoding='utf-8')))
        expected_hit = run['mode'] != 'no-cache' and run['scenario'] in ('warm', 'source')
        assert run['dependency_cached'] is expected_hit, (run['mode'], run['scenario'], run['repeat'])
    # Compare actual materialized bases, not only FROM spelling.
    bases = {tuple(r['smoke']['rootfs_diffids'][:4]) for r in report['runs']}
    assert len(bases) == 1, 'Different materialized Python bases invalidate comparison'
    for mode in modes:
        for scenario in SCENARIOS:
            samples = [r for r in report['runs'] if r['mode'] == mode and r['scenario'] == scenario]
            assert {r['repeat'] for r in samples} == set(range(report['repeats']))
            row = {'mode': mode, 'scenario': scenario, 'samples': len(samples)}
            for metric in ('seconds', 'dependency_seconds', 'cache_import_seconds',
                           'cache_export_seconds', 'cache_transfer_span_seconds'):
                values = [r[metric] for r in samples]
                row[metric] = statistics.median(values) if all(v is not None for v in values) else None
            row['dependency_hits'] = sum(r['dependency_cached'] for r in samples)
            row['image_size_bytes'] = [r['smoke']['size_bytes'] for r in samples]
            rows.append(row)
    summary = {'source_sha': report['source_sha'], 'session': report['session'],
               'repeats': report['repeats'], 'runs': len(report['runs']),
               'release_image': False, 'hosted_gha': 'Not measured',
               'cloud_build_only': 'Not measured', 'rows': rows,
               'builder_setup_seconds': [r['seconds'] for r in report['setup_seconds']],
               'cleanup_errors': report.get('cleanup_errors'),
               'same_materialized_base': True}
    summary['samples'] = [{k: run[k] for k in (
        'mode', 'scenario', 'repeat', 'seconds', 'success', 'dependency_seconds',
        'dependency_cached', 'cache_import_seconds', 'cache_export_seconds',
        'cache_transfer_span_seconds', 'smoke')} for run in report['runs']]
    summary['environment'] = {k: report[k] for k in (
        'host', 'resources', 'buildx', 'buildkit_image', 'default_builder', 'docker')
        if k in report}
    summary['inputs'] = {path.parent.name: json.loads(path.read_text(encoding='utf-8'))
                         for path in sorted(output.glob('trial-*/inputs.json'))}
    write_json(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'run', 'summary'))
    parser.add_argument('--sha')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3, choices=range(2, 6))
    args = parser.parse_args()
    output = args.output.resolve()
    # Refuse contexts/cache outside this checkout's ignored QA directory.
    if not output.is_relative_to((ROOT / 'local-data/ci-003').resolve()):
        parser.error('Output must be a new directory under local-data/ci-003')
    if args.operation == 'summary':
        print(json.dumps(summarize(output), indent=2))
    elif not args.sha:
        parser.error('--sha is required for prepare/run')
    elif args.operation == 'prepare':
        prepare(args.sha, output)
    else:
        benchmark(args.sha, output, args.repeats)


if __name__ == '__main__':
    main()
