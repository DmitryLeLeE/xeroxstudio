"""Веб-версия строится из тех же констант, что и программа: файлы не должны расходиться."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(script):
    return subprocess.run([sys.executable, str(ROOT / "tools" / script), "--check"],
                          capture_output=True, text=True, cwd=ROOT)


def test_web_config_is_in_sync_with_python_config():
    r = _run("gen_config_js.py")
    assert r.returncode == 0, r.stderr or r.stdout


def test_service_worker_precache_is_current():
    r = _run("gen_sw.py")
    assert r.returncode == 0, r.stderr or r.stdout
