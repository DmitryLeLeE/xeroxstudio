"""
Project IO: чтение и запись проектов .zine (zip: manifest.json + images/*.png).

Запись атомарная: сначала временный файл, потом замена, поэтому сбой посреди сохранения
не портит уже существующий проект. Модуль не зависит от Tk и безопасен для фонового потока.
"""

import json
import os
import zipfile

import cv2
import numpy as np

FORMAT_VERSION = 2


def _json_default(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, (set, tuple)):
        return list(obj)
    raise TypeError(f"{type(obj).__name__} нельзя сохранить в проект")


def write_project(path, pages, images, cur):
    used = sorted({k for p in pages for k in [p.get("img"), *[ly.get("img") for ly in (p.get("layers") or []) if isinstance(ly, dict)]] if k in images})
    manifest = {"version": FORMAT_VERSION, "pages": pages, "cur": cur, "images": used}
    tmp = f"{path}.tmp"
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False, default=_json_default))
            for key in used:
                ok, buf = cv2.imencode(".png", images[key])
                if not ok:
                    raise ValueError(f"не удалось закодировать фото {key}")
                zf.writestr(f"images/{key}.png", buf.tobytes())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def read_project(path):
    """Возвращает (pages, images, cur). Бросает ValueError/OSError/BadZipFile на испорченном файле."""
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        if "manifest.json" not in names:
            raise ValueError("это не проект .zine (нет manifest.json)")
        data = json.loads(zf.read("manifest.json").decode("utf-8"))
        pages = data.get("pages")
        if not isinstance(pages, list) or not pages or not all(isinstance(p, dict) for p in pages):
            raise ValueError("в проекте нет страниц")

        images = {}
        for name in names:
            if name.startswith("images/") and name.endswith(".png"):
                img = cv2.imdecode(np.frombuffer(zf.read(name), np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    images[os.path.basename(name)[:-4]] = img
        if "source.png" in names:  # проекты первой версии: одно фото на все страницы
            legacy = cv2.imdecode(np.frombuffer(zf.read("source.png"), np.uint8), cv2.IMREAD_COLOR)
            if legacy is not None:
                images["legacy"] = legacy
                for p in pages:
                    p.setdefault("img", "legacy")

    cur = data.get("cur", 0)
    cur = min(max(0, cur if isinstance(cur, int) else 0), len(pages) - 1)
    return pages, images, cur
