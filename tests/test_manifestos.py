import config
import manifestos


def test_builtin_library_is_complete():
    items = manifestos.builtin()
    assert len(items) == len(config.ZINE_QUOTES) >= 110
    assert {i["lang"] for i in items} == {"en"}
    for i in items:
        assert i["top"] and i["bottom"] and i["cat"], i
        assert "[" not in i["top"], "тег категории не должен попадать в текст"
    assert manifestos.categories(items) == ["VISION", "SURVEILLANCE", "MEMORY", "BRUTAL", "POST-PUNK", "COPIER", "DIY", "CITY", "ХАНДРА", "БЕССОННИЦА", "ГОРОД", "ИТ-ВЫГОРАНИЕ", "ПАМЯТЬ", "ЗИН", "GLOOM", "ROOT"]


def test_filter_by_source_category_and_query():
    items = manifestos.builtin()
    vision = manifestos.filter_items(items, "en", "VISION")
    assert vision and all(i["cat"] == "VISION" for i in vision)
    assert manifestos.filter_items(items, "all", "", "toner")
    assert manifestos.filter_items(items, "all", "", "TONER")  # регистр не важен
    assert manifestos.filter_items(items, "user") == []
    assert manifestos.filter_items(items, "all", "", "no-such-phrase-xyz") == []


def test_user_manifestos(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert manifestos.save_user("МОЙ ТЕКСТ", "ВНИЗУ") is True
    assert manifestos.save_user("МОЙ ТЕКСТ", "ВНИЗУ") is False  # дубликат
    assert manifestos.save_user("  ", "") is False
    user = manifestos.filter_items(manifestos.all_items(), "user")
    assert len(user) == 1 and user[0]["cat"] == "Мои"
    assert manifestos.delete_user("МОЙ ТЕКСТ", "ВНИЗУ") is True
    assert manifestos.load_user() == []


def test_broken_user_file_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    import appdata
    open(f"{appdata.data_dir()}/manifestos.json", "w", encoding="utf-8").write('[{"top": 1}, "x", {"top": "a", "bottom": "b"}]')
    assert [i["top"] for i in manifestos.load_user()] == ["a"]


def test_label_is_short_single_line():
    item = {"lang": "en", "cat": "X", "top": "A\nB" * 30, "bottom": "C\nD" * 30}
    text = manifestos.label(item, 58)
    assert len(text) <= 58 and "\n" not in text
