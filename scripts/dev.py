"""Small cross-platform adapters for Make; no application or gcloud implementation.

Bootstrap-compatible with Python 3.9+. Runtime commands use .venv Python 3.12+.
"""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
BROWSERS = (
    "browser_spa_smoke.py",
    "browser_smoke.py", "browser_hub_smoke.py", "browser_document_studio_smoke.py",
    "browser_marketing_smoke.py", "browser_trip_documents_smoke.py", "browser_cloud_preview_smoke.py",
    "browser_cloud_demo_smoke.py", "browser_gt_templates.py",
)


def run(command, *, env=None):
    # No shell, no echoing arguments that might contain configuration values.
    result = subprocess.run([str(arg) for arg in command], cwd=ROOT, env=env)
    if result.returncode:
        raise SystemExit(result.returncode)


def venv_python():
    executable = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        raise ValueError("Missing .venv; run make install-dev (or make install) first")
    return str(executable)


def install(development=False):
    executable = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.exists():
        bootstrap = [sys.executable]
        if sys.version_info < (3,12):
            if os.name == "nt" and shutil.which("py"):
                bootstrap = ["py", "-3.12"]
            elif shutil.which("python3.12"):
                bootstrap = ["python3.12"]
            else:
                raise ValueError("Python 3.12+ required; select its executable with make install PYTHON=...")
        run([*bootstrap, "-m", "venv", str(ROOT / ".venv")])
    run([str(executable), "-c", "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"])
    run([str(executable), "-m", "pip", "install", "-r", "requirements-dev.txt" if development else "requirements.txt"])


def local_environment():
    env = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for number,line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(),1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key,sep,value = line.partition("=")
            key,value = key.strip(),value.strip()
            if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",key):
                raise ValueError(f"Invalid .env syntax at line {number}; expected KEY=value")
            if len(value)>=2 and value[0]==value[-1] and value[0] in "\"'":
                value=value[1:-1]
            if "$" in value or "`" in value:
                raise ValueError(f"Interpolation is unsupported in .env at line {number}; set a literal or shell variable")
            env.setdefault(key,value)
    if env.get("K_SERVICE") or env.get("CLOUD_FEATURE_MODE","local") != "local":
        raise ValueError("Local target requires local runtime; unset K_SERVICE/CLOUD_FEATURE_MODE from cloud configuration")
    if env.get("PLANNING_MODE","live") not in {"mock","live"}:
        raise ValueError("PLANNING_MODE must be mock or live")
    return env


def validate_live(executable, env):
    # Reuse the existing provider contract. Construction does not call paid APIs.
    code=("import sys\nfrom app.planning import configured_generator\n"
          "from app.planning_providers import PlanningError\n"
          "try: configured_generator()\n"
          "except PlanningError as error:\n print(str(error), file=sys.stderr)\n sys.exit(1)\n")
    run([executable,"-c",code],env=env)


def local(target):
    executable = venv_python()
    env = local_environment()
    if target in {"dev-mock","dev-live"}:
        env["PLANNING_MODE"] = "mock" if target=="dev-mock" else "live"
    if target=="dev-live" or (target=="worker" and env.get("PLANNING_MODE","live")=="live"):
        validate_live(executable,env)
    if target=="worker":
        run([executable,"-m","app.worker"],env=env)
        return
    host = os.getenv("HOST") or "127.0.0.1"
    port = os.getenv("PORT") or env.get("API_PORT") or "8000"
    if host not in {"127.0.0.1","localhost","::1"} or not port.isdigit() or not 1<=int(port)<=65535:
        raise ValueError("Use a loopback HOST and PORT between 1 and 65535")
    print(f"Local API, planning mode {env.get('PLANNING_MODE','live')}; start the worker separately with the same mode and DATABASE_PATH",flush=True)
    run([executable,"-m","uvicorn","app.main:app","--host",host,"--port",port],env=env)


def docker(target):
    commands = {
        "docker-up":["up","--build","-d","api","worker"], "docker-down":["down"],
        "docker-build":["build","api","worker"], "docker-logs":["logs","--follow"],
        "docker-ps":["ps"], "docker-restart":["restart","api","worker"],
        "docker-mock":["up","--build","-d","--force-recreate","api","worker"],
        "docker-waha":["--profile","whatsapp","up","--build","-d","api","worker","waha"],
    }
    env = dict(os.environ)
    if target=="docker-mock":
        env["PLANNING_MODE"]="mock"
    # Never implicitly use the public compose.dev.yaml or profiles from the shell.
    env.pop("COMPOSE_PROFILES",None)
    run(["docker","compose","-f","compose.yaml",*commands[target]],env=env)


def gcp(target):
    environment = os.getenv("ENV","")
    if target in {"gcp-preflight","gcp-smoke","gcp-dry-run"}:
        environment = environment or "dev"
    if target in {"deploy-dev","deploy-prod"}:
        required = "dev" if target=="deploy-dev" else "prod"
        if environment and environment!=required:
            raise ValueError("ENV conflicts with the selected deploy target")
        environment=required
    if environment not in {"dev","prod"}:
        raise ValueError("Specify ENV=dev or ENV=prod (mutating gcp-* targets have no default)")
    tag,confirm = os.getenv("TAG",""),os.getenv("CONFIRM","")
    if tag:
        # Import the same validator as deployment.py; do not maintain a second SHA contract.
        from scripts.gcp.deployment_contract import image_tag
        image_tag(tag)
    if target=="deploy-prod" and (not tag or confirm!="prod"):
        raise ValueError("deploy-prod requires TAG=<commit SHA> CONFIRM=prod")
    if target=="gcp-rollback" and (not tag or confirm!="rollback"):
        raise ValueError("gcp-rollback requires TAG=<commit SHA> CONFIRM=rollback")
    if target in {"gcp-setup","gcp-build"} and environment!="dev":
        raise ValueError("Use ENV=dev for shared setup/build; PROD promotes an existing image")
    actions = {"gcp-preflight":"preflight","gcp-setup":"setup","gcp-build":"build","deploy-dev":"deploy",
               "deploy-prod":"deploy","gcp-smoke":"smoke","gcp-rollback":"rollback","gcp-dry-run":"deploy"}
    command=[venv_python(),"scripts/gcp/deployment.py",actions[target],"--environment",environment]
    if tag:command += ["--image-tag",tag]
    if os.getenv("CONFIG_DIR"):command += ["--config-dir",os.environ["CONFIG_DIR"]]
    if target=="gcp-dry-run":command.append("--dry-run")
    offline=os.getenv("OFFLINE","")
    if offline not in {"","0","1"}:raise ValueError("OFFLINE must be 0 or 1")
    if offline=="1":
        if target!="gcp-preflight":raise ValueError("OFFLINE=1 is supported only by gcp-preflight")
        command.append("--offline")
    run(command)


def test_environment(directory):
    env=dict(os.environ,PLANNING_MODE="mock",CLOUD_FEATURE_MODE="local",
             DATABASE_PATH=str(Path(directory)/"planner.sqlite3"), DOCUMENT_STUDIO_DATA_PATH=str(Path(directory)/"documents"),
             PUBLIC_BASE_URL="http://localhost:8000",WORKER_POLL_SECONDS="0.1")
    for key in ("K_SERVICE","EXPECTED_IMAGE_SHA","OPENAI_API_KEY","GOOGLE_MAPS_API_KEY","GOOGLE_PLACES_API_KEY",
                "GOOGLE_ROUTES_API_KEY","GOOGLE_MAPS_BROWSER_KEY","WAHA_API_KEY","WAHA_WEBHOOK_HMAC_KEY","DOCUMENT_STUDIO_DOCKER_LOCAL"):
        env.pop(key,None)
    return env


def stop(process):
    if process.poll() is not None:return
    # Windows venv python.exe is a launcher: stop its owned child tree as well.
    if os.name=="nt":
        subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.kill();process.wait()


def legacy_browser(executable, env):
    # This script alone expects an existing mock worker; supply an isolated origin.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",0))
        port=listener.getsockname()[1]
    base=f"http://localhost:{port}"
    env=dict(env,PUBLIC_BASE_URL=base,TRIPSE_BROWSER_BASE_URL=base)
    processes=[]
    with tempfile.TemporaryDirectory(prefix="tripse-make-logs-") as logs:
        with (Path(logs)/"api-worker.log").open("w") as log:
            try:
                api=subprocess.Popen([executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(port),"--no-access-log"],cwd=ROOT,env=env,stdout=log,stderr=log)
                processes.append(api)
                opener=build_opener(ProxyHandler({}))
                for _ in range(100):
                    if api.poll() is not None:raise ValueError("Temporary browser API failed to start")
                    try:
                        with opener.open(base+"/health",timeout=1) as response:
                            if json.load(response).get("generation_mode")=="mock":break
                    except URLError:pass
                    time.sleep(.1)
                else:raise ValueError("Temporary browser API readiness timeout")
                processes.append(subprocess.Popen([executable,"-m","app.worker"],cwd=ROOT,env=env,stdout=log,stderr=log))
                run([executable,"tests/browser_demo_smoke.py"],env=env)
            finally:
                for process in reversed(processes):
                    stop(process)


def tests(target):
    executable=venv_python()
    with tempfile.TemporaryDirectory(prefix="tripse-make-tests-") as directory:
        env=test_environment(directory)
        if target in {"test","test-unit","test-all"}:run([executable,"-m","pytest","-q"],env=env)
        if target in {"test-browser","test-all"}:
            for script in BROWSERS:run([executable,"tests/"+script],env=env)
            legacy_browser(executable,env)
        if target in {"test-container","test-all"}:run([executable,"tests/container_cloud_preview_smoke.py"],env=env)


def demo(target):
    paths={"demo-hub":"/hub","demo-docs":"/documents/demo","demo-planner":"/planner","demo-whatsapp":"/demo/chat"}
    env=local_environment()
    base=os.getenv("BASE_URL") or "http://localhost:"+(os.getenv("PORT") or env.get("API_PORT") or "8000")
    parsed=urlsplit(base)
    if parsed.scheme not in {"http","https"} or parsed.hostname not in {"localhost","127.0.0.1","::1"} or parsed.username or parsed.password or parsed.path not in {"","/"} or parsed.query or parsed.fragment:
        raise ValueError("BASE_URL must be a loopback HTTP(S) origin")
    url=base.rstrip("/")+paths[target]
    print(url,flush=True)
    if target=="demo-whatsapp":print("Requires PLANNING_MODE=mock in BOTH the running API and worker; make dev-mock / make worker PLANNING_MODE=mock",flush=True)
    try:
        with build_opener(ProxyHandler({})).open(base.rstrip("/")+"/health",timeout=3) as response:
            health=json.load(response)
    except (OSError,ValueError):
        raise ValueError("Local API is not healthy; start make dev-mock first. No server was started") from None
    if health.get("feature_mode")=="readonly_demo":raise ValueError("This demo target requires the local runtime, not cloud preview")
    if target=="demo-whatsapp" and health.get("generation_mode")!="mock":raise ValueError("Running API is not mock; restart it explicitly with make dev-mock")
    try:opened=webbrowser.open(url)
    except (webbrowser.Error,OSError):opened=False
    if not opened:print("Could not open a browser; open the URL above manually")


def linked(path):
    # Python 3.9 bootstrap also has to reject Windows junctions/reparse points.
    return path.is_symlink() or bool(getattr(path.lstat(),"st_file_attributes",0) & getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0))


def clean():
    # Never traverse virtualenvs, user data, fixture assets, symlinks or junctions.
    allowed=[ROOT/".pytest_cache"]
    for base in (ROOT/"app",ROOT/"scripts",ROOT/"tests"):
        if not base.exists() or linked(base):continue
        for directory,children,_ in os.walk(base,followlinks=False):
            children[:]=[name for name in children if not linked(Path(directory)/name)]
            for name in list(children):
                if name=="__pycache__":allowed.append(Path(directory)/name);children.remove(name)
    for path in allowed:
        if not path.exists():continue
        if linked(path) or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Refusing cleanup outside the workspace or through a link")
        shutil.rmtree(path)
    print("Removed only .pytest_cache and app/scripts/tests Python caches; user data preserved")


def doctor():
    print(f"Bootstrap Python: {sys.version.split()[0]} ({sys.executable})")
    try:executable=venv_python()
    except ValueError:executable=sys.executable;print(".venv: missing; run make install-dev")
    else:print(".venv: present")
    for name,command in (("Python",[executable,"--version"]),("pip",[executable,"-m","pip","--version"]),
                         ("Git",["git","--version"]),("GNU Make",["make","--version"]),
                         ("Docker",["docker","version","--format","{{.Server.Version}}"]),("Compose",["docker","compose","version"]),
                         ("gcloud (optional)",["gcloud","--version"])):
        try:result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=20)
        except (OSError,subprocess.TimeoutExpired):print(name+": unavailable")
        else:print(name+": "+(result.stdout.splitlines()[0] if result.returncode==0 and result.stdout else "unavailable/not running"))
    print("PowerShell: "+("available" if shutil.which("pwsh") or shutil.which("powershell") else "not installed")+"; not required by Make targets (GCP uses Python)")
    # Diagnostic report, not an all-tools-required gate. Targets validate their own tools.


def main(target):
    if target=="doctor":doctor()
    elif target in {"install","install-dev"}:install(target=="install-dev")
    elif target=="install-browser":run([venv_python(),"-m","playwright","install","chromium"])
    elif target in {"dev","dev-mock","dev-live","worker"}:local(target)
    elif target.startswith("docker-"):docker(target)
    elif target in {"test","test-unit","test-browser","test-container","test-all"}:tests(target)
    elif target=="check":
        run(["git","diff","--check"])
        run(["docker","compose","-f","compose.yaml","config","--quiet"])
    elif target.startswith("demo-"):demo(target)
    elif target.startswith("gcp-") or target in {"deploy-dev","deploy-prod"}:gcp(target)
    elif target=="clean":clean()
    else:raise ValueError("Unknown target; use make help")


if __name__=="__main__":
    sys.path.insert(0,str(ROOT))
    try:main(sys.argv[1])
    except (OSError,ValueError) as error:
        print(f"MAKE: {error}",file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:sys.exit(130)
