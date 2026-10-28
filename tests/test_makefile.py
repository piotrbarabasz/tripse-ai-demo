"""Make wrappers: process delegation and safety, without live providers or GCP."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import dev


@pytest.fixture
def commands(monkeypatch):
    result=[]
    monkeypatch.setattr(dev,"run",lambda args,**kwargs:result.append((list(map(str,args)),kwargs)))
    monkeypatch.setattr(dev,"venv_python",lambda:"python path with spaces/python")
    for key in ("ENV","TAG","CONFIRM","CONFIG_DIR","OFFLINE","HOST","PORT","BASE_URL"):
        monkeypatch.delenv(key,raising=False)
    return result


@pytest.mark.parametrize("target,values,message",[
    ("deploy-prod",{},"TAG"), ("deploy-prod",{"TAG":"a"*40},"CONFIRM"),
    ("deploy-prod",{"CONFIRM":"prod"},"TAG"),
    ("deploy-prod",{"TAG":"latest","CONFIRM":"prod"},"SHA"),
    ("gcp-setup",{},"ENV"), ("gcp-build",{"ENV":"prod"},"dev"),
    ("gcp-smoke",{"ENV":"staging"},"ENV"),
    ("deploy-dev",{"ENV":"prod"},"conflicts"),
    ("gcp-rollback",{"ENV":"dev","TAG":"a"*40},"CONFIRM"),
    ("gcp-preflight",{"OFFLINE":"yes"},"OFFLINE"),
])
def test_gcp_guards(commands,monkeypatch,target,values,message):
    for key,value in values.items():monkeypatch.setenv(key,value)
    with pytest.raises(ValueError,match=message):dev.gcp(target)
    assert not commands


def test_gcp_delegation_and_quoting(commands,monkeypatch):
    monkeypatch.setenv("TAG","a"*40);monkeypatch.setenv("CONFIRM","prod")
    monkeypatch.setenv("CONFIG_DIR","C:/config folder")
    dev.gcp("deploy-prod")
    args=commands[-1][0]
    assert args==["python path with spaces/python","scripts/gcp/deployment.py","deploy","--environment","prod","--image-tag","a"*40,"--config-dir","C:/config folder"]
    monkeypatch.delenv("TAG");monkeypatch.setenv("ENV","dev")
    dev.gcp("gcp-dry-run")
    assert "--dry-run" in commands[-1][0]
    monkeypatch.setenv("OFFLINE","1")
    dev.gcp("gcp-preflight")
    assert "--offline" in commands[-1][0]
    assert all("gcloud" not in command for command,_ in commands)


def test_docker_contract_and_mock(commands,monkeypatch):
    monkeypatch.setenv("COMPOSE_PROFILES","whatsapp,dev")
    for target in ("docker-up","docker-down","docker-build","docker-logs","docker-ps","docker-restart","docker-mock","docker-waha"):
        dev.docker(target)
    up=commands[0][0];down=commands[1][0]
    assert up==["docker","compose","-f","compose.yaml","up","--build","-d","api","worker"]
    assert down[-1]=="down" and "--volumes" not in down and "-v" not in down
    assert commands[-2][1]["env"]["PLANNING_MODE"]=="mock"
    assert commands[-1][0][4:6]==["--profile","whatsapp"]
    assert all("COMPOSE_PROFILES" not in kwargs["env"] for _,kwargs in commands)


def test_env_file_shell_precedence_and_no_secret_output(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(dev,"ROOT",tmp_path)
    monkeypatch.delenv("CLOUD_FEATURE_MODE",raising=False);monkeypatch.delenv("K_SERVICE",raising=False)
    (tmp_path/".env").write_text("PLANNING_MODE=live\nOPENAI_API_KEY='example-not-a-real-secret'\n")
    monkeypatch.setenv("PLANNING_MODE","mock")
    env=dev.local_environment()
    assert env["PLANNING_MODE"]=="mock" and env["OPENAI_API_KEY"]=="example-not-a-real-secret"
    assert not capsys.readouterr().out


def test_local_modes_and_worker(commands,monkeypatch):
    monkeypatch.setattr(dev,"local_environment",lambda:{"PLANNING_MODE":"live"})
    dev.local("dev-mock")
    assert commands[-1][1]["env"]["PLANNING_MODE"]=="mock"
    assert "uvicorn" in commands[-1][0]
    commands.clear();dev.local("dev-live")
    assert "configured_generator" in commands[0][0][-1]
    assert commands[-1][1]["env"]["PLANNING_MODE"]=="live"
    commands.clear();dev.local("worker")
    assert commands[-1][0][-1]=="app.worker"


def test_clean_preserves_all_user_data(tmp_path,monkeypatch):
    monkeypatch.setattr(dev,"ROOT",tmp_path)
    protected=[".env",".env.dev",".env.prod","data/tripse.sqlite3","local-data/document-studio/drafts/draft.json",
               "local-data/document-studio/assets/photo.png","local-data/__pycache__/keep.pyc","demo-fixtures/trips/keep.json"]
    caches=[".pytest_cache/v/cache/lastfailed","app/__pycache__/module.pyc","scripts/gcp/__pycache__/module.pyc","tests/__pycache__/test.pyc"]
    for name in protected+caches:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text("keep")
    dev.clean()
    assert all((tmp_path/name).read_text()=="keep" for name in protected)
    assert all(not (tmp_path/name).exists() for name in caches)


def test_clean_rejects_cache_junction(tmp_path,monkeypatch):
    monkeypatch.setattr(dev,"ROOT",tmp_path)
    protected=tmp_path/"local-data";protected.mkdir();(protected/"keep.txt").write_text("keep")
    cache=tmp_path/".pytest_cache"
    if os.name=="nt":
        subprocess.run(["cmd","/c","mklink","/J",str(cache),str(protected)],check=True,capture_output=True)
    else:cache.symlink_to(protected,target_is_directory=True)
    with pytest.raises(ValueError,match="link"):dev.clean()
    assert (protected/"keep.txt").read_text()=="keep"


def test_process_failure_preserves_child_code(monkeypatch):
    monkeypatch.setattr(dev.subprocess,"run",lambda *a,**kw:type("Result",(),{"returncode":23})())
    with pytest.raises(SystemExit) as error:dev.run(["fake"])
    assert error.value.code==23


def test_all_browser_scripts_accounted_for():
    actual={p.name for p in (dev.ROOT/"tests").glob("browser*.py")}
    assert actual==set(dev.BROWSERS)|{"browser_demo_smoke.py"}


def test_demo_opens_existing_api_or_prints_url(commands,monkeypatch,capsys):
    monkeypatch.setattr(dev,"local_environment",lambda:{"PLANNING_MODE":"mock"})
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self):return b'{"generation_mode":"mock","status":"ok"}'
    monkeypatch.setattr(dev,"build_opener",lambda *args:type("Opener",(),{"open":lambda *a,**kw:Response()})())
    urls=[]
    monkeypatch.setattr(dev.webbrowser,"open",lambda url:urls.append(url) or False)
    for target in ("demo-hub","demo-docs","demo-planner","demo-whatsapp"):dev.demo(target)
    assert urls==["http://localhost:8000/hub","http://localhost:8000/documents/demo","http://localhost:8000/planner","http://localhost:8000/demo/chat"]
    assert not commands  # Never starts another API or worker.
    assert "open the URL above manually" in capsys.readouterr().out
    monkeypatch.setenv("BASE_URL","https://example.com")
    with pytest.raises(ValueError,match="loopback"):dev.demo("demo-hub")


def test_make_propagates_child_failure(tmp_path):
    make=shutil.which("make")
    if not make:pytest.skip("GNU Make not on PATH")
    shutil.copy2(dev.ROOT/"Makefile",tmp_path/"Makefile")
    (tmp_path/"scripts").mkdir()
    (tmp_path/"scripts/dev.py").write_text("import sys; sys.exit(23)\n")
    result=subprocess.run([make,"doctor","PYTHON="+sys.executable],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode!=0 and "23" in result.stderr


@pytest.mark.parametrize("args,marker",[
    (["deploy-prod"],"TAG"), (["deploy-prod","TAG="+"a"*40],"CONFIRM"),
    (["gcp-preflight","ENV=invalid"],"ENV"),
])
def test_real_make_refuses_unsafe_operations(args,marker):
    make=shutil.which("make")
    if not make:pytest.skip("GNU Make not on PATH")
    result=subprocess.run([make,*args,"PYTHON="+sys.executable],cwd=dev.ROOT,capture_output=True,text=True)
    assert result.returncode!=0 and marker in result.stderr


def test_help_without_python_or_optional_tools(tmp_path):
    make=shutil.which("make")
    if not make:pytest.skip("GNU Make not on PATH")
    # Native Make itself needs a valid Windows COMSPEC; no Unix tools/Python are available.
    tool_path=str(Path(make).parent)
    if os.name=="nt":tool_path+=os.pathsep+str(Path(os.environ["SystemRoot"])/"System32")
    env=dict(os.environ,PATH=tool_path)
    result=subprocess.run([make,"help","PYTHON=missing-python"],cwd=dev.ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0 and "deploy-prod" in result.stdout and "CONFIRM=prod" in result.stdout
