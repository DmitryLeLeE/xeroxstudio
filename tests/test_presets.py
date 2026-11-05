import config
import presets


def test_builtin_presets_are_valid():
    for name, style in presets.all_presets().items():
        assert set(style) == set(presets.STYLE_KEYS), name
        assert style["layout"] in config.LAYOUTS.values(), name
        assert style["dither"] in config.DITHERS.values(), name
        assert style["tstyle"] in config.TEXT_STYLES.values(), name
        assert style["font"] in config.FONT_FILES, name
        assert style["palette"] in config.RISO_PALETTES or style["palette"] == config.CUSTOM_PALETTE, name


def test_user_presets_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    state = dict(config.DEFAULT_STATE, dot_size=13, txt_top="не должно попасть в пресет")
    presets.save_user("мой стиль", state)
    got = presets.load_user()["мой стиль"]
    assert got["dot_size"] == 13 and "txt_top" not in got and "img" not in got
    assert "мой стиль" in presets.all_presets()
    presets.delete_user("мой стиль")
    assert "мой стиль" not in presets.load_user()


def test_broken_presets_file_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    import appdata
    open(f"{appdata.data_dir()}/presets.json", "w", encoding="utf-8").write("{не json")
    assert presets.load_user() == {}


def test_all_builtin_presets_render_and_use_known_layouts():
    import numpy as np
    from engine import ZineGraphicEngine
    eng = ZineGraphicEngine()
    img = np.random.default_rng(3).integers(0, 255, (300, 400, 3), dtype=np.uint8)
    assert len(presets.BUILTIN) >= 20
    for name, p in presets.BUILTIN.items():
        assert p.get("layout", "staggered") in config.LAYOUTS.values(), name
        st = {**config.DEFAULT_STATE, **p, "txt_top": "A", "txt_bottom": "B"}
        out, _ = eng.render_zine_page(img, st, scale=0.3)
        assert out.size[0] > 100, name
