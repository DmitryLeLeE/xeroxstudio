"""
Manifestos: библиотека готовых английских манифестов и пользовательские («Мои»).

Элемент: {"lang": "en" (готовый) | "user" (свой), "cat": категория, "top": текст, "bottom": текст}.
"""

import json
import os
import re

import appdata
import config

LANG_LABELS = {"all": "Все", "en": "Готовые", "user": "Мои"}
USER_CATEGORY = "Мои"
_TAG = re.compile(r"^\[(.+?)\]\s*(.*)$", re.S)


def _parse(raw, lang):
    top, bottom = raw
    m = _TAG.match(top)
    cat, top = (m.group(1), m.group(2)) if m else ("", top)
    return {"lang": lang, "cat": cat.strip(), "top": top.strip(), "bottom": bottom.strip()}


def builtin():
    return [_parse(q, "en") for q in config.ZINE_QUOTES]


def _user_path():
    return os.path.join(appdata.data_dir(), "manifestos.json")


def load_user():
    try:
        with open(_user_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    items = []
    for d in data if isinstance(data, list) else []:
        if isinstance(d, dict) and isinstance(d.get("top"), str) and isinstance(d.get("bottom"), str):
            items.append({"lang": "user", "cat": USER_CATEGORY, "top": d["top"], "bottom": d["bottom"]})
    return items


def _write_user(items):
    tmp = _user_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump([{"top": i["top"], "bottom": i["bottom"]} for i in items], f, ensure_ascii=False, indent=2)
    os.replace(tmp, _user_path())


def save_user(top, bottom):
    """Сохраняет свой манифест. False, если такой уже есть или оба текста пусты."""
    top, bottom = top.strip(), bottom.strip()
    if not (top or bottom):
        return False
    items = load_user()
    if any(i["top"] == top and i["bottom"] == bottom for i in items):
        return False
    items.append({"lang": "user", "cat": USER_CATEGORY, "top": top, "bottom": bottom})
    _write_user(items)
    return True


def delete_user(top, bottom):
    items = load_user()
    kept = [i for i in items if not (i["top"] == top.strip() and i["bottom"] == bottom.strip())]
    if len(kept) != len(items):
        _write_user(kept)
        return True
    return False


def all_items():
    return builtin() + load_user()


def categories(items):
    seen = []
    for i in items:
        if i["cat"] and i["cat"] not in seen:
            seen.append(i["cat"])
    return seen


def filter_items(items, lang="all", cat="", query=""):
    q = query.strip().lower()
    out = []
    for i in items:
        if lang != "all" and i["lang"] != lang:
            continue
        if cat and i["cat"] != cat:
            continue
        if q and q not in (i["top"] + " " + i["bottom"]).lower():
            continue
        out.append(i)
    return out


def label(item, width=58):
    text = item["top"].replace("\n", " ") + "  /  " + item["bottom"].replace("\n", " ")
    return text if len(text) <= width else text[: width - 1] + "…"
