"""Optional local Docker QA, separate from Cloud Build/deploy; cleans up only its own resources."""
import json
from http.client import RemoteDisconnected
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]


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
            shutil.copytree(ROOT/"app",context/"app",ignore=shutil.ignore_patterns("__pycache__","*.pyc","_build_version.txt"))
            for name in ("gt-v1",):
                shutil.copytree(ROOT/"demo-fixtures"/name,context/"demo-fixtures"/name)
            (context/"app/_build_version.txt").write_text("a"*40)
            command("build","--platform=linux/amd64","-t",image,str(context))
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
        try:urlopen(Request(base+"/api/trips",method="POST"),timeout=5)
        except HTTPError as error:assert error.code==403
        else:raise AssertionError("Write API exposed")
        # --rm removes the container after stop; logs are captured first by following wait.
        waiter=subprocess.Popen(["docker","wait",container],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        command("stop","--time=10",container)
        output,_=waiter.communicate(timeout=15)
        assert output.strip()=="0",output
        container=None
        print("Container PASS: linux/amd64, port 8000, read-only filesystem, baked SHA, fixtures, write denial, SIGTERM exit 0")
    finally:
        if container:
            subprocess.run(["docker","rm","-f",container],capture_output=True)
        subprocess.run(["docker","image","rm",image],capture_output=True)


if __name__=="__main__":main()
