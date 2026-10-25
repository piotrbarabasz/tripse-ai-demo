"""Offline preflight with a real uvicorn process; no optional testing dependency."""
import json
import os
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Cloud startup failed")
            try:
                with urlopen(base+"/health", timeout=1) as response:
                    health = json.load(response)
                    assert health["feature_mode"] == "readonly_demo"
                    assert health["environment"] == os.environ["APP_ENV"]
                break
            except URLError:
                time.sleep(.1)
        else:
            raise RuntimeError("Startup timeout")
        for path in ("/hub", "/preview/planner", "/preview/documents/collection?variant=new_trips", "/preview/documents/collection?variant=theme_collection", "/documents/assets/print-export.js"):
            with urlopen(base+path, timeout=10) as response:
                assert response.status == 200
        for path, method in (("/api/trips", "POST"), ("/api/document-studio/drafts", "POST"), ("/documents/demo", "GET"), ("/demo/chat", "GET")):
            try:
                urlopen(Request(base+path, method=method), timeout=5)
            except HTTPError as error:
                assert error.code in {403,404}
            else:
                raise AssertionError("Forbidden endpoint was exposed")
    finally:
        process.terminate()
        process.wait(timeout=15)


if __name__ == "__main__":
    main()
