"""Optional local Docker QA, separate from Cloud Build/deploy; cleans up only its own resources."""
import json
from http.client import RemoteDisconnected
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def command(*args):
    return subprocess.check_output(["docker",*args],cwd=ROOT,text=True,stderr=subprocess.STDOUT).strip()


def main():
    image="tripse-cloud-qa:"+uuid4().hex[:12]
    container=None
    try:
        with tempfile.TemporaryDirectory(prefix="tripse-container-qa-") as directory:
            context=Path(directory)
            for name in ("Dockerfile","requirements.txt",".dockerignore"):
                shutil.copy2(ROOT/name,context/name)
            shutil.copytree(ROOT/"app",context/"app",ignore=shutil.ignore_patterns("__pycache__","*.pyc","_build_version.txt","spa_dist"))
            from scripts.gcp.frontend_build import is_frontend_input
            for source in (ROOT/"frontend").rglob("*"):
                name=source.relative_to(ROOT).as_posix()
                if source.is_file() and is_frontend_input(name):
                    target=context/name;target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,target)
            for name in ("gt-v1",):
                shutil.copytree(ROOT/"demo-fixtures"/name,context/"demo-fixtures"/name)
            (context/"app/_build_version.txt").write_text("a"*40)
            command("build","--platform=linux/amd64","-t",image,str(context))
        command("run","--rm","--entrypoint","python",image,"-c",
                "from pathlib import Path; import shutil; assert not shutil.which('node'); assert not shutil.which('npm'); "
                "assert not list(Path('/app').rglob('node_modules')); assert Path('/app/app/spa_dist/index.html').is_file(); "
                "assert list(Path('/app/app/spa_dist/assets').glob('*.js')); assert list(Path('/app/app/spa_dist/assets').glob('*.css'))")
        container=command("run","--rm","-d","--read-only","--tmpfs","/tmp","--cap-drop=ALL","--pids-limit=128",
                          "-p","127.0.0.1::8000","-e","APP_ENV=dev","-e","PLANNING_MODE=mock","-e","CLOUD_FEATURE_MODE=readonly_demo",
                          "-e","K_SERVICE=tripse-ai-dev","-e","EXPECTED_IMAGE_SHA="+"a"*40,image)
        mapping=command("port",container,"8000/tcp")
        base="http://"+mapping
        for _ in range(100):
            try:
                with urlopen(base+"/health",timeout=1) as response:
                    health=json.load(response)
                    assert health["image_version"]=="a"*40 and health["environment"]=="dev"
                break
            except (URLError, RemoteDisconnected, ConnectionResetError):time.sleep(.1)
        else:raise RuntimeError("Container readiness timeout")
        with urlopen(base+"/preview/documents/collection",timeout=5) as response:assert response.status==200
        for path in ("/app", "/app/assets/missing.js"):
            try:urlopen(base+path,timeout=5)
            except HTTPError as error:assert error.code==404
            else:raise AssertionError("Private SPA exposed in readonly image mode")
        try:urlopen(Request(base+"/api/trips",method="POST"),timeout=5)
        except HTTPError as error:assert error.code==403
        else:raise AssertionError("Write API exposed")
        # --rm removes the container after stop; logs are captured first by following wait.
        waiter=subprocess.Popen(["docker","wait",container],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        command("stop","--time=10",container)
        output,_=waiter.communicate(timeout=15)
        assert output.strip()=="0",output
        container=None
        container=command("run","--rm","-d","--read-only","--tmpfs","/tmp","--cap-drop=ALL","--pids-limit=128",
                          "-p","127.0.0.1::8000","-e","PLANNING_MODE=mock","-e","CLOUD_FEATURE_MODE=local",
                          "-e","DATABASE_PATH=/tmp/tripse.sqlite3","-e","DOCUMENT_STUDIO_DATA_PATH=/tmp/documents",
                          "-e","DOCUMENT_STUDIO_DOCKER_LOCAL=1",image)
        base="http://"+command("port",container,"8000/tcp")
        for _ in range(100):
            try:
                with urlopen(base+"/health",timeout=1) as response:assert json.load(response)["status"]=="ok"
                break
            except (URLError, RemoteDisconnected, ConnectionResetError):time.sleep(.1)
        else:raise RuntimeError("Local container readiness timeout")
        for path in ("/app", "/app/planner"):
            with urlopen(Request(base+path,headers={"Accept":"text/html"}),timeout=5) as response:
                assert response.status==200 and b'id="root"' in response.read()
                assert "unsafe-inline" not in response.headers["Content-Security-Policy"]
        command("stop","--time=10",container);container=None
        print("Container PASS: linux/amd64, Python-only runtime with compiled SPA, readonly exclusion, local entry/deep link, port 8000, read-only filesystem, baked SHA, fixtures, write denial, SIGTERM exit 0")
    finally:
        if container:
            subprocess.run(["docker","rm","-f",container],capture_output=True)
        subprocess.run(["docker","image","rm",image],capture_output=True)


if __name__=="__main__":main()
