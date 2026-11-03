"""
AppData: папка данных приложения, настройки пользователя и журнал ошибок.

Всё лежит в %LOCALAPPDATA%\\XeroxZineStudio (на других ОС - ~/.local/share/XeroxZineStudio):
    app.log        журнал (ротация, до ~1.5 МБ)
    settings.json  последние папки, масштаб экспорта
    autosave.zine  автосохранение на случай аварийного закрытия
"""

import json
import logging
import logging.handlers
import os
import tempfile

_DIR_NAME = "XeroxZineStudio"


def data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    for candidate in (os.path.join(base, _DIR_NAME), os.path.join(tempfile.gettempdir(), _DIR_NAME)):
        try:
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except OSError:
            continue
    return tempfile.gettempdir()


def log_path():
    return os.path.join(data_dir(), "app.log")


def autosave_path():
    return os.path.join(data_dir(), "autosave.zine")


def setup_logging():
    log = logging.getLogger("zine")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    try:
        handler = logging.handlers.RotatingFileHandler(log_path(), maxBytes=512_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(handler)
    except OSError:
        log.addHandler(logging.NullHandler())
    return log


class Settings:
    """Небольшой JSON-файл настроек. Повреждённый или отсутствующий файл не мешает запуску."""

    def __init__(self):
        self.path = os.path.join(data_dir(), "settings.json")
        self.data = {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data = loaded
        except (OSError, ValueError):
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            logging.getLogger("zine").warning("не удалось сохранить настройки", exc_info=True)
