import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(tmp_path, main_source):
    work = tmp_path / "app"
    work.mkdir(parents=True)
    shutil.copy(os.path.join(HERE, "launcher.py"), work / "launcher.py")
    (work / "main.py").write_text(main_source, encoding="utf-8")
    # ZINE_NO_DIALOG: на Windows не открывать настоящее окно ошибки во время тестов
    env = dict(os.environ, LOCALAPPDATA=str(tmp_path / "data"), ZINE_NO_DIALOG="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, str(work / "launcher.py")], capture_output=True, encoding="utf-8", env=env, timeout=60)
    log = tmp_path / "data" / "XeroxZineStudio" / "crash.log"
    return proc, (log.read_text(encoding="utf-8") if log.exists() else "")


def test_import_failure_explains_missing_runtime(tmp_path):
    proc, log = _run(tmp_path, 'raise ImportError("DLL load failed while importing cv2")\n')
    assert proc.returncode == 1
    assert "DLL load failed while importing cv2" in proc.stderr
    assert "vc_redist.x64.exe" in proc.stderr          # человек видит, что и откуда поставить
    assert "crash.log" in proc.stderr and "DLL load failed" in log


def test_runtime_failure_is_reported_without_redist_hint(tmp_path):
    proc, log = _run(tmp_path, "def main():\n    raise RuntimeError('boom')\n")
    assert proc.returncode == 1
    assert "boom" in proc.stderr and "vc_redist" not in proc.stderr
    assert "RuntimeError" in log


def test_normal_start_passes_and_exit_code_is_kept(tmp_path):
    proc, log = _run(tmp_path / "ok", "def main():\n    pass\n")
    assert proc.returncode == 0 and log == ""
    proc, _ = _run(tmp_path / "exit3", "import sys\n\ndef main():\n    sys.exit(3)\n")  # --selftest возвращает код через sys.exit
    assert proc.returncode == 3
