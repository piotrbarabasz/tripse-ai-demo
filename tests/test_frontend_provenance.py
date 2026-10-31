"""Exact frontend source/lock/pin proofs, including pre-integration compatibility."""
import io
import tarfile
from pathlib import Path

import pytest

from scripts.gcp import build_proof as proof, deployment as d
from scripts.gcp.frontend_build import CONFIG_FILES, MARKER, is_frontend_input, validate_frontend_source

ROOT = Path(__file__).resolve().parents[1]


def archive(files, mode="w"):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode=mode) as stream:
        for name, data in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            stream.addfile(member, io.BytesIO(data))
    return result.getvalue()


@pytest.fixture
def inputs():
    files = {name:(ROOT/name).read_bytes() for name in CONFIG_FILES}
    files.update({"Dockerfile":(ROOT/"Dockerfile").read_bytes(), "app/main.py":b"# application",
                  "frontend/src/main.tsx":b"// bootstrap"})
    return files


def test_source_selects_exact_build_inputs_but_never_outputs_or_env(monkeypatch, inputs):
    inputs.update({name: (ROOT/name).read_bytes() for name in (
        "frontend/src/shared/api/generated/types.gen.ts", "frontend/src/shared/api/generated/zod.gen.ts",
        "frontend/src/features/planner/PlannerPage.tsx", "frontend/src/features/planner/result.ts",
        "frontend/src/features/documents/DocumentsWorkspace.tsx", "frontend/src/features/documents/links.ts")})
    unwanted = {name:b"ignored" for name in ("docs/api/openapi.json", "frontend/scripts/generate-api.mjs", "frontend/.env.local", "frontend/dist/index.html", "app/spa_dist/index.html",
        "frontend/node_modules/pkg/index.js", "frontend/coverage/index.html", "frontend/.vite/cache.ts", "frontend/tsconfig.tsbuildinfo",
        "frontend/src/.cache/file.ts", "frontend/README.md", "frontend/eslint.config.js", "local-data/private.json")}
    monkeypatch.setattr(d, "run", lambda *a, **kw: archive(inputs | unwanted))
    assert dict(d.source_files("a"*40)) == inputs
    validate_frontend_source(inputs)


def test_historical_python_only_recipe_does_not_gain_frontend_context(monkeypatch, inputs):
    old = inputs | {"Dockerfile":b"FROM python:3.12-slim\n"}
    monkeypatch.setattr(d, "run", lambda *a, **kw: archive(old))
    selected = dict(d.source_files("a"*40))
    assert set(selected) == {"Dockerfile", "app/main.py"}
    # accepted-release rollback keeps the old context manifest unchanged.
    assert proof.context_manifest(selected) == proof.context_manifest({name:old[name] for name in selected})


@pytest.mark.parametrize("name", sorted(CONFIG_FILES | {"frontend/src/main.tsx"}))
def test_missing_frontend_build_input_fails_closed(inputs, name):
    del inputs[name]
    with pytest.raises(ValueError, match="incomplete"):
        validate_frontend_source(inputs)


@pytest.mark.parametrize("attack", ["node_pin", "python_pin", "floating_node", "install", "copy", "node_version", "lock"])
def test_unreviewed_build_inputs_rejected(inputs, attack):
    if attack in {"node_pin", "python_pin"}:
        image = b"node:" if attack == "node_pin" else b"python:"
        lines = inputs["Dockerfile"].splitlines()
        inputs["Dockerfile"] = b"\n".join(line.replace(b"sha256:", b"sha256:0") if line.startswith(b"FROM " + image) else line for line in lines)
    elif attack == "floating_node": inputs["Dockerfile"] = inputs["Dockerfile"].replace(b"@sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d", b"")
    elif attack == "install": inputs["Dockerfile"] = inputs["Dockerfile"].replace(b"npm ci", b"npm install")
    elif attack == "copy": inputs["Dockerfile"] = inputs["Dockerfile"].replace(b"COPY --from=frontend-build /build/frontend/dist ./app/spa_dist", b"COPY --from=frontend-build /build/frontend ./app/spa_dist")
    elif attack == "node_version": inputs["frontend/.nvmrc"] = b"26.0.0"
    elif attack == "lock": inputs["frontend/package-lock.json"] = b'{"lockfileVersion":3,"packages":{}}'
    with pytest.raises(ValueError): validate_frontend_source(inputs)


@pytest.mark.parametrize("name", ["frontend/package-lock.json", "frontend/vite.config.ts", "frontend/src/main.tsx", "frontend/src/shared/api/generated/types.gen.ts", "frontend/src/shared/api/generated/zod.gen.ts", "Dockerfile"])
def test_exact_manifest_and_archive_reject_changed_frontend_bytes(inputs, name):
    if name.startswith("frontend/src/shared/api/generated/"):
        inputs[name] = (ROOT/name).read_bytes()
    expected = inputs | {"app/_build_version.txt":b"a"*40}
    changed = expected | {name:expected[name]+b"\n"}
    assert proof.context_manifest(changed) != proof.context_manifest(expected)
    proof.validate_archive(archive(expected, "w:gz"), expected)
    with pytest.raises(ValueError): proof.validate_archive(archive(changed, "w:gz"), expected)
    with pytest.raises(ValueError): proof.validate_archive(archive({k:v for k,v in expected.items() if k != name}, "w:gz"), expected)
    with pytest.raises(ValueError): proof.validate_archive(archive(expected | {"frontend/dist/poison.js":b"poison"}, "w:gz"), expected)


def test_symlink_and_secret_checks_still_apply(monkeypatch, inputs):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as stream:
        member = tarfile.TarInfo("Dockerfile"); member.type = tarfile.SYMTYPE; member.linkname = "outside"
        stream.addfile(member)
    monkeypatch.setattr(d, "run", lambda *a, **kw: raw.getvalue())
    with pytest.raises(ValueError, match="Unsafe"): dict(d.source_files("a"*40))
    assert MARKER in inputs["Dockerfile"]
    assert is_frontend_input("frontend/src/health.ts")
    with pytest.raises(ValueError, match="credential"):
        d.validate_source_file("frontend/src/config.ts", b'"private_key": "never disclose"')
