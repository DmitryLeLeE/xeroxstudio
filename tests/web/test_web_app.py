import json

import pytest

from conftest import wait_ready




def test_app_loads_clean_with_paper_theme_and_landmarks(page_factory):
    pg = page_factory()
    wait_ready(pg)
    assert pg.errors == []
    assert pg.evaluate("document.documentElement.dataset.theme") == "paper"
    assert pg.evaluate("document.querySelectorAll('h1').length") == 1
    assert pg.evaluate("document.querySelector('canvas#preview').getAttribute('role')") == "img"


def test_theme_toggle_persists(page_factory):
    pg = page_factory()
    wait_ready(pg)
    pg.click("#btnTheme")
    assert pg.evaluate("document.documentElement.dataset.theme") == "dark"
    assert pg.evaluate("localStorage.getItem('zine.theme')") == '"dark"'
    pg.reload()
    wait_ready(pg)
    assert pg.evaluate("document.documentElement.dataset.theme") == "dark"


def test_all_builtin_presets_render(page_factory):
    pg = page_factory()
    wait_ready(pg)
    options = pg.evaluate("[...document.querySelectorAll('#presetRow select option')].map(o => o.value).filter(Boolean)")
    assert len(options) >= 9
    for name in options[:9]:
        pg.select_option("#presetRow select", name)
        pg.wait_for_timeout(500)
    assert pg.errors == []
    # на холсте что-то нарисовано (не пустой белый лист)
    dark = pg.evaluate("""() => { const c = document.querySelector('#preview'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        let n = 0; for (let i = 0; i < d.length; i += 40) if (d[i] < 100) n++; return n; }""")
    assert dark > 100


def test_manifesto_library_has_54_and_write_your_own(page_factory):
    pg = page_factory(width=1440, height=860)
    wait_ready(pg)
    pg.keyboard.press("Control+m")
    pg.wait_for_selector("dialog[open]")
    assert pg.inner_text("#mCount").startswith("54 of 54")
    pg.click("#mWrite")
    pg.fill("#mNewTop", "make noise\nnot content")
    pg.fill("#mNewBottom", "print it yourself")
    pg.click("#mNewSave")
    pg.wait_for_timeout(300)
    assert pg.inner_text("#mCount").startswith("1 of 55")
    assert "PRINT IT YOURSELF" in pg.inner_text("#mPrev")
    # кнопка закрытия не перекрыта другими элементами
    covered = pg.evaluate("""() => { const e = document.querySelector('dialog[open] .dlg-head button'); const r = e.getBoundingClientRect();
        return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) !== e; }""")
    assert not covered
    pg.click("dialog[open] .dlg-head button")
    assert pg.evaluate("!document.querySelector('dialog[open]')")


def test_png_download_is_a_png(page_factory):
    pg = page_factory()
    wait_ready(pg)
    pg.evaluate("window.showSaveFilePicker = undefined")
    with pg.expect_download() as dl:
        pg.click("#btnSavePng")
    path = dl.value.path()
    assert open(path, "rb").read(8) == b"\x89PNG\r\n\x1a\n"


def test_first_run_shows_welcome_dialog(page_factory):
    pg = page_factory(welcomed=False)
    wait_ready(pg)
    assert pg.evaluate("document.querySelector('#dlgWelcome').open")
    pg.click("#wSample")
    assert not pg.evaluate("document.querySelector('#dlgWelcome').open")
    assert pg.evaluate("localStorage.getItem('zine.welcomed')") == "true"


@pytest.mark.parametrize("width,height", [(320, 568), (390, 844)])
def test_phone_has_no_horizontal_overflow(page_factory, width, height):
    pg = page_factory(mobile=True, width=width, height=height)
    wait_ready(pg)
    assert pg.evaluate("document.documentElement.scrollWidth") <= width
    for tab in ("photo", "style", "text", "view"):
        pg.tap(f"#tabbar [data-go={tab}]")
        pg.wait_for_timeout(150)
        assert pg.evaluate("document.documentElement.scrollWidth") <= width


def test_zine_roundtrip_through_page_state(page_factory):
    """Состояние страницы сериализуется в JSON и содержит новые ключи эффектов."""
    pg = page_factory()
    wait_ready(pg)
    state = pg.evaluate("JSON.stringify(window.__zine.page())")
    data = json.loads(state)
    for key in ("paper", "overprint", "ink2", "tape"):
        assert key in data


def test_landing_page_clean_and_bilingual(page_factory):
    pg = page_factory("/", lang="en")
    pg.wait_for_selector("h1")
    assert pg.errors == []
    assert "zines" in pg.inner_text("h1").lower()
    pg.click("#lang")
    assert "зины" in pg.inner_text("h1").lower()
    assert pg.evaluate("document.querySelectorAll('.wall figure').length") == 9


def test_layouts_match_python_engine(page_factory):
    """Геометрия кадров в JS и в Python должна совпадать для всех раскладок."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import config
    from engine import ZineGraphicEngine

    pg = page_factory()
    wait_ready(pg)
    layouts = sorted(config.LAYOUTS.values())
    cases = [(lay, rows, 1000, 1500) for lay in layouts for rows in (1, 3, 5, 8)]
    js = pg.evaluate(
        """async (cases) => { const m = await import('/app/js/engine.js');
           return cases.map(([l, r, w, h]) => m.layoutBoxes(l, w, h, r, 12)); }""", cases)
    for (lay, rows, w, h), got in zip(cases, js):
        want = [list(b) for b in ZineGraphicEngine._layout_boxes(lay, w, h, rows, 12, 1.0)]
        assert got == want, (lay, rows)
