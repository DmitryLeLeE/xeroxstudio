"""
Launcher: точка входа для собранного exe.

Приложение без консоли при сбое запуска (например, нет системной библиотеки) просто не
открывается и ничего не объясняет. Здесь ошибка перехватывается: человек видит окно с причиной
и ссылкой на нужный компонент, а подробности пишутся в crash.log.
"""

import os
import sys
import tempfile
import traceback

VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"

DLL_HINT = (
    "Чаще всего это значит, что на компьютере нет «Microsoft Visual C++ Redistributable 2015–2022 (x64)».\n"
    "Скачайте и установите его, затем запустите программу снова:\n" + VC_REDIST_URL + "\n\n"
    "Если установка не помогла: программа работает только в 64-разрядной Windows 10 и новее."
)


def crash_log_path():
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    folder = os.path.join(base, "XeroxZineStudio")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = tempfile.gettempdir()
    return os.path.join(folder, "crash.log")


def show_error(text):
    # ZINE_NO_DIALOG=1 печатает в stderr вместо окна (так проверяют launcher автотесты)
    if sys.platform == "win32" and not os.environ.get("ZINE_NO_DIALOG"):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, "Xerox Zine Studio", 0x10)  # MB_ICONERROR
            return
        except Exception:
            pass
    try:
        print(text, file=sys.stderr)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"), file=sys.stderr)


def report(exc_text, is_import_problem):
    path = crash_log_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(exc_text + "\n")
    except OSError:
        pass
    last = exc_text.strip().splitlines()[-1] if exc_text.strip() else "неизвестная ошибка"
    head = "Не удалось запустить Xerox Zine Studio.\n\n" + last + "\n\n"
    tail = (DLL_HINT + "\n\n") if is_import_problem else ""
    show_error(head + tail + "Подробности записаны в файл:\n" + path)


def run():
    try:
        import main  # импорт тянет numpy, OpenCV, Pillow и Tk: здесь видно, чего не хватает
    except BaseException:
        report(traceback.format_exc(), is_import_problem=True)
        return 1
    try:
        main.main()
    except SystemExit:
        raise
    except Exception:
        report(traceback.format_exc(), is_import_problem=False)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
