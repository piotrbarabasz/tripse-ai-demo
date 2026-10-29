"""Cross-workstream checks; dirty integration bytes never become a Git release."""
import io
from pathlib import Path
import subprocess
import tarfile

import pytest

from scripts.gcp import build_proof, registry_audit
from scripts.gcp.deployment import source_files
from scripts.gcp.deployment_contract import Config
from tests.test_github_cicd import values

ROOT = Path(__file__).resolve().parents[1]


def test_working_context_cannot_masquerade_as_committed_provenance():
    sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    expected = dict(source_files(sha)) | {'app/_build_version.txt':sha.encode()}
    working = {name: ((ROOT/name).read_bytes() if name != 'app/_build_version.txt' else sha.encode())
               for name in expected}
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw,mode='w:gz') as stream:
        for name,data in working.items():
            info=tarfile.TarInfo(name);info.size=len(data)
            stream.addfile(info,io.BytesIO(data))
    if working != expected:
        with pytest.raises(ValueError):build_proof.validate_archive(raw.getvalue(),expected)
    else:
        build_proof.validate_archive(raw.getvalue(),expected)
    assert not any(name.startswith(('scripts/','docs/','tests/','.github/','local-data/')) for name in expected)


def test_inventory_and_release_contract_identify_the_same_existing_registry():
    config=Config(values())
    assert registry_audit.REPOSITORY == (f'projects/{config["GCP_PROJECT_ID"]}/locations/'
                                       f'{config["GCP_REGION"]}/repositories/{config["GCP_ARTIFACT_REPO"]}')
    assert config.image == registry_audit.PREFIX + config['GCP_IMAGE_NAME']
