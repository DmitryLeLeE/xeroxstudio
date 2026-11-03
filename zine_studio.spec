# -*- mode: python ; coding: utf-8 -*-
# Обычно запускается через build.py. Вручную:  pyinstaller --noconfirm --clean zine_studio.spec
# Переменная ZINE_ONEDIR=1 собирает папку вместо одного exe.
import os
import sys

ONEDIR = os.environ.get("ZINE_ONEDIR") == "1"
VERSION_FILE = "version_info.txt" if os.path.exists("version_info.txt") else None

datas = [
    ("icon.ico", "."), ("icon.png", "."),
    ("assets/haarcascade_frontalface_default.xml", "."),
    ("THIRD_PARTY_NOTICES.md", "."),
]
binaries = []
hiddenimports = ["PIL._tkinter_finder"]

# Библиотеки среды выполнения Visual C++. На чистом Windows их нет, и без msvcp140.dll
# не загружается OpenCV (ImportError: DLL load failed while importing cv2). Кладём рядом с программой
# (app-local deployment разрешён Microsoft). Нужны на машине, где идёт сборка: build.py это проверяет.
if sys.platform == "win32":
    _sysdir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    for _dll in ("msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "msvcp140_atomic_wait.dll",
                 "msvcp140_codecvt_ids.dll", "concrt140.dll", "vcruntime140.dll", "vcruntime140_1.dll",
                 "vcomp140.dll"):
        _path = os.path.join(_sysdir, _dll)
        if os.path.exists(_path):
            binaries.append((_path, "."))

# Перетаскивание файлов: tkinterdnd2 тянет за собой нативную библиотеку tkdnd
try:
    from PyInstaller.utils.hooks import collect_all
    _d, _b, _h = collect_all("tkinterdnd2")
    datas += _d
    binaries += _b
    hiddenimports += _h
except Exception:
    pass

# Каскад Хаара для «чёрной полосы на глазах» лежит в assets/ и копируется в корень сборки:
# он не зависит от версии OpenCV (в пакете opencv 5.x его уже нет).

a = Analysis(
    ["launcher.py"],
    # launcher.py показывает понятное сообщение, если на чужом ПК чего-то не хватает
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "IPython", "pytest", "numpy.tests"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEDIR:
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True, name="XeroxZineStudio", icon="icon.ico",
        version=VERSION_FILE, debug=False, strip=False, upx=False, console=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="XeroxZineStudio")
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [], name="XeroxZineStudio", icon="icon.ico",
        version=VERSION_FILE, debug=False, strip=False, upx=False, console=False, runtime_tmpdir=None,
    )
