"""
Сборка Xerox Zine Studio одной командой:

    python build.py              один файл dist/XeroxZineStudio.exe
    python build.py --onedir     папка + zip (быстрее стартует, реже ругается антивирус)
    python build.py --installer  + установщик dist/XeroxZineStudio-Setup-<версия>.exe (нужен Inno Setup 6)
    python build.py --no-install не ставить зависимости (если уже стоят)

Скрипт сам: ставит зависимости, рисует иконку, прогоняет тесты, собирает exe через PyInstaller
и проверяет готовый файл встроенным самотестом (--selftest).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

sys.path.insert(0, ROOT)
import config  # noqa: E402

NAME = "XeroxZineStudio"
EXT = ".exe" if sys.platform == "win32" else ""


def run(cmd, env=None):
    print("\n» " + " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT, env=env)


def step(text):
    print(f"\n=== {text} ===", flush=True)


def write_version_file():
    parts = [int(p) for p in config.APP_VERSION.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    tup = tuple(parts) + (0,)
    dotted = ".".join(map(str, tup))
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', ''),
      StringStruct('FileDescription', '{config.APP_NAME}'),
      StringStruct('FileVersion', '{dotted}'),
      StringStruct('InternalName', '{NAME}'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', '{config.APP_NAME}'),
      StringStruct('ProductVersion', '{dotted}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open(os.path.join(ROOT, "version_info.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def find_iscc():
    found = shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            for sub in ("Inno Setup 6", os.path.join("Programs", "Inno Setup 6")):
                candidate = os.path.join(base, sub, "ISCC.exe")
                if os.path.exists(candidate):
                    return candidate
    return None


def build_installer():
    step("Установщик Inno Setup")
    iscc = find_iscc() if sys.platform == "win32" else None
    if not iscc:
        sys.exit("Не найден Inno Setup 6 (ISCC.exe). Установите: https://jrsoftware.org/isdl.php  (или: winget install JRSoftware.InnoSetup)")
    run([iscc, f"/DAppVersion={config.APP_VERSION}", "installer.iss"])
    print(f"\nУстановщик: dist\\{NAME}-Setup-{config.APP_VERSION}.exe")


REQUIRED_WIN_DLLS = ("msvcp140.dll", "vcruntime140.dll")


def bundled_names(exe, onedir):
    """Имена файлов (в нижнем регистре), которые попали в сборку."""
    if onedir:
        root = os.path.dirname(exe)
        return {f.lower() for _d, _s, files in os.walk(root) for f in files}
    from PyInstaller.archive.readers import CArchiveReader
    reader = CArchiveReader(exe)
    return {os.path.basename(str(name)).lower() for name in reader.toc}


def check_runtime_on_build_machine():
    """Без msvcp140.dll на этом компьютере exe не получит её и не запустится на чистом Windows."""
    if sys.platform != "win32":
        return
    sysdir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    if not os.path.exists(os.path.join(sysdir, "msvcp140.dll")):
        sys.exit("На этом компьютере нет msvcp140.dll, её не из чего вшить в exe.\n"
                 "Установите Microsoft Visual C++ Redistributable (x64): https://aka.ms/vs/17/release/vc_redist.x64.exe")


def verify_runtime_bundled(exe, onedir):
    names = bundled_names(exe, onedir)
    if sys.platform == "win32":
        missing = [d for d in REQUIRED_WIN_DLLS if d not in names]
        if missing:
            sys.exit(f"В сборку не попали {', '.join(missing)}: на чистом Windows программа не запустится.")
    return names


def main():
    ap = argparse.ArgumentParser(description="Сборка Xerox Zine Studio")
    ap.add_argument("--onedir", action="store_true", help="папка вместо одного exe (+ zip)")
    ap.add_argument("--installer", action="store_true", help="собрать установщик Inno Setup (включает --onedir)")
    ap.add_argument("--no-install", action="store_true", help="не устанавливать зависимости")
    ap.add_argument("--skip-tests", action="store_true", help="не запускать pytest перед сборкой")
    args = ap.parse_args()

    args.onedir = args.onedir or args.installer
    if sys.version_info < (3, 10):
        sys.exit("Нужен Python 3.10 или новее.")
    try:
        import tkinter  # noqa: F401
    except ImportError:
        sys.exit("Не найден tkinter. Переустановите Python с галочкой «tcl/tk and IDLE».")

    if not args.no_install:
        step("1/5 Зависимости")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "-r", "requirements.txt", "-r", "requirements-build.txt"])

    step("2/5 Иконка")
    run([sys.executable, "make_icon.py"])

    if not args.skip_tests:
        step("3/5 Тесты")
        run([sys.executable, "-m", "pytest", "-q", "tests"])

    step("4/5 Сборка PyInstaller")
    check_runtime_on_build_machine()
    write_version_file()
    for d in ("build", "dist"):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
    env = dict(os.environ, ZINE_ONEDIR="1" if args.onedir else "0")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "zine_studio.spec"], env=env)

    exe = os.path.join(ROOT, "dist", NAME, NAME + EXT) if args.onedir else os.path.join(ROOT, "dist", NAME + EXT)
    if not os.path.exists(exe):
        sys.exit(f"Сборка завершилась, но файл не найден: {exe}")

    step("5/5 Проверка собранного файла")
    names = verify_runtime_bundled(exe, args.onedir)
    print(f"Состав сборки проверен: файлов {len(names)}" + (", библиотеки Visual C++ на месте" if sys.platform == "win32" else ""))
    out = os.path.join(tempfile.mkdtemp(), "selftest.json")
    proc = subprocess.run([exe, "--selftest", out], timeout=300)
    result = {}
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            result = json.load(f)
    if proc.returncode != 0 or not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit("Самотест собранного файла не пройден: приложение не готово к выдаче.")
    print("Самотест пройден:", ", ".join(result["checks"]))
    if not result.get("info", {}).get("drag_and_drop"):
        print("ВНИМАНИЕ: не найден tkinterdnd2/tkdnd, перетаскивание файлов в окно работать не будет.")

    if args.onedir:
        archive = shutil.make_archive(os.path.join(ROOT, "dist", f"{NAME}-{config.APP_VERSION}"), "zip", os.path.join(ROOT, "dist", NAME))
        print(f"\nГотово: {exe}\nАрхив:  {archive}")
        if args.installer:
            build_installer()
    else:
        print(f"\nГотово: {exe}  ({os.path.getsize(exe) / 1e6:.0f} МБ)")


if __name__ == "__main__":
    main()
