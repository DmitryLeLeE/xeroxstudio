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
    open(f"{appdata.data_dir()}/presets.json", "w").write("{не json")
    assert presets.load_user() == {}
