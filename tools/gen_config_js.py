"""Генерирует web/app/js/config.js из config.py, presets.py и manifestos.py.

    python tools/gen_config_js.py          # записать файл
    python tools/gen_config_js.py --check  # только проверить, что файл актуален (для CI)
"""
import sys, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import config, presets, manifestos, stickers

def pairs(d): return [[k, v] for k, v in d.items()]
fonts = {
  "Arial Black":          {"css": '"Arial Black", "Rubik", sans-serif', "weight": 900},
  "Arial Bold":           {"css": 'Arial, "Rubik", sans-serif', "weight": 700},
  "Impact":               {"css": 'Impact, "Oswald", sans-serif', "weight": 400},
  "Courier New Bold":     {"css": '"Courier New", "JetBrains Mono", monospace', "weight": 700},
  "Consolas Bold":        {"css": 'Consolas, "JetBrains Mono", monospace', "weight": 700},
  "Times New Roman Bold": {"css": '"Times New Roman", "PT Serif", serif', "weight": 700},
  "Rubik Mono One":       {"css": '"Rubik Mono One", "Rubik", sans-serif', "weight": 400},
  "Press Start 2P":       {"css": '"Press Start 2P", "JetBrains Mono", monospace', "weight": 400},
  "Marck Script":         {"css": '"Marck Script", cursive', "weight": 400},
  "Special Elite":        {"css": '"Special Elite", "JetBrains Mono", monospace', "weight": 400},
  "Permanent Marker":     {"css": '"Permanent Marker", "Rubik", sans-serif', "weight": 400},
  "Rubik Dirt":           {"css": '"Rubik Dirt", "Rubik", sans-serif', "weight": 400},
  "Rubik Distressed":     {"css": '"Rubik Distressed", "Rubik", sans-serif', "weight": 400},
  "Rubik Wet Paint":      {"css": '"Rubik Wet Paint", "Rubik", sans-serif', "weight": 400},
  "Rubik Spray Paint":    {"css": '"Rubik Spray Paint", "Rubik", sans-serif', "weight": 400},
  "Rubik Glitch":         {"css": '"Rubik Glitch", "Rubik", sans-serif', "weight": 400},
}
assert set(fonts) == set(config.FONT_FILES)
data = {
  "APP_VERSION": config.APP_VERSION,
  "CANVAS_FORMATS": {k: list(v) for k, v in config.CANVAS_FORMATS.items()},
  "RISO_PALETTES": {k: [list(a), list(b)] for k, (a, b) in config.RISO_PALETTES.items()},
  "CUSTOM_PALETTE": config.CUSTOM_PALETTE,
  "LAYOUTS": pairs(config.LAYOUTS), "LAYOUT_ALIASES": config.LAYOUT_ALIASES,
  "DITHERS": pairs(config.DITHERS), "FIT_MODES": pairs(config.FIT_MODES),
  "TEXT_STYLES": pairs(config.TEXT_STYLES), "TEXT_ALIGNS": pairs(config.TEXT_ALIGNS),
  "FONTS": fonts,
  "DEFAULT_STATE": {k: ([list(c) for c in v] if k == "custom_colors" else v) for k, v in config.DEFAULT_STATE.items()},
  "STYLE_KEYS": list(presets.STYLE_KEYS),
  "BUILTIN_PRESETS": {k: {kk: ([list(c) for c in vv] if kk == "custom_colors" else vv) for kk, vv in v.items()} for k, v in presets.all_presets().items() if k in presets.BUILTIN},
  "MANIFESTOS": manifestos.builtin(),
  "STICKERS": {k: {"ru": v[0], "en": v[1], "prims": v[2]} for k, v in stickers.STICKERS.items()},
}
text = ("// Сгенерировано из config.py и presets.py (tools/gen_config_js.py). Не править вручную.\n"
        "export const CFG = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
target = os.path.join(ROOT, "web", "app", "js", "config.js")
if "--check" in sys.argv:
    cur = open(target, encoding="utf-8", newline="").read() if os.path.exists(target) else ""
    if cur != text:
        sys.exit("web/app/js/config.js is stale: run python tools/gen_config_js.py")
    print("config.js is up to date")
else:
    open(target, "w", encoding="utf-8", newline="\n").write(text)
    print(len(data["MANIFESTOS"]), "manifestos,", len(data["BUILTIN_PRESETS"]), "presets")
