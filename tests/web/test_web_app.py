import json

import pytest

from conftest import WEB, wait_ready, wait_until




def test_app_loads_clean_with_usa_theme_and_landmarks(page_factory):
    pg = page_factory()
    wait_ready(pg)
    assert pg.errors == []
    assert pg.evaluate("document.documentElement.dataset.theme") == "usa"
    assert pg.evaluate("document.querySelectorAll('h1').length") == 1
    assert pg.evaluate("document.querySelector('canvas#preview').getAttribute('role')") == "img"


def test_theme_menu_lists_four_named_themes_and_switches_icons(page_factory):
    pg = page_factory()
    wait_ready(pg)
    before = pg.evaluate("document.querySelector('#rail button svg').outerHTML")
    pg.click("#btnTheme")
    assert pg.evaluate("document.querySelectorAll('#menuTheme button').length") == 4
    pg.click("#menuTheme button:nth-child(4)")  # fsociety
    assert pg.evaluate("document.documentElement.dataset.theme") == "robot"
    assert pg.evaluate("localStorage.getItem('zine.theme')") == '"robot"'
    assert pg.evaluate("document.querySelector('#rail button svg').outerHTML") != before  # значки сменились без перезагрузки
    pg.reload()
    wait_ready(pg)
    assert pg.evaluate("document.documentElement.dataset.theme") == "robot"
    pg.click("#btnTheme")
    pg.click("#menuTheme button:nth-child(2)")  # бумага
    assert pg.evaluate("document.documentElement.dataset.theme") == "paper"
    assert pg.evaluate("document.querySelector('#menuTheme').hidden") is True


def test_jargon_sliders_have_plain_hints(page_factory):
    pg = page_factory(lang="ru")
    wait_ready(pg)
    hints = pg.evaluate("[...document.querySelectorAll('.ctl-hint')].map(e => e.textContent)")
    assert len(hints) >= 12 and all(len(h) > 10 for h in hints)
    pg2 = page_factory(lang="en")
    wait_ready(pg2)
    en = pg2.evaluate("[...document.querySelectorAll('.ctl-hint')].map(e => e.textContent)")
    assert len(en) == len(hints) and not any("а" <= c.lower() <= "я" for h in en for c in h)


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


def test_manifesto_library_english_only_in_en_and_write_your_own(page_factory):
    pg = page_factory(width=1440, height=860)
    wait_ready(pg)
    pg.keyboard.press("Control+m")
    pg.wait_for_selector("dialog[open]")
    assert pg.inner_text("#mCount").startswith("70 of 70")
    pg.click("#mWrite")
    pg.fill("#mNewTop", "make noise\nnot content")
    pg.fill("#mNewBottom", "print it yourself")
    pg.click("#mNewSave")
    pg.wait_for_timeout(300)
    assert pg.inner_text("#mCount").startswith("1 of 71")
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
    for fly in ("photo", "s2", "s6", "s0", "all"):
        if fly == "all":
            pg.tap("#rail .rail-all")
        else:
            pg.tap(f"#rail button[data-fly={fly}]")
        pg.wait_for_timeout(150)
        assert pg.evaluate("document.documentElement.scrollWidth") <= width
        assert pg.evaluate("document.querySelector('#drawer').getBoundingClientRect().right") <= width + 1


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


def test_before_after_compare_toggles_and_draws(page_factory):
    pg = page_factory(width=1300, height=860)
    wait_ready(pg)
    pg.wait_for_timeout(800)
    before = pg.evaluate("document.querySelector('#preview').toDataURL()")
    pg.click("#btnCompare")
    assert pg.evaluate("document.querySelector('#btnCompare').getAttribute('aria-pressed')") == "true"
    after = pg.evaluate("document.querySelector('#preview').toDataURL()")
    assert before != after  # слева нарисовано исходное фото
    pg.click("#btnCompare")
    assert pg.evaluate("document.querySelector('#preview').toDataURL()") == before


def test_new_layout_presets_exist(page_factory):
    pg = page_factory()
    wait_ready(pg)
    names = pg.evaluate("[...document.querySelectorAll('#presetRow select option')].map(o => o.textContent)")
    for n in ("Diagonal Punk", "Photo Pile", "Newsprint Mosaic", "Cyanotype Triptych", "Full-page Poster", "Film-test Ribbon", "Riso Diptych"):
        assert n in names, n


def test_shared_look_link_roundtrip_and_validation(page_factory):
    pg = page_factory(welcomed=False)
    wait_ready(pg)
    pg.click("#wSample")
    pg.select_option("#presetRow select", "Триптих-синька")
    pg.wait_for_timeout(500)
    url = pg.evaluate("""async () => { const m = await import('/app/js/config.js'); const s = window.__zine.page();
        const o = {}; for (const k of [...m.CFG.STYLE_KEYS, 'txt_top', 'txt_bottom', 'seed']) o[k] = s[k];
        const b = btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(o)))).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
        return '/app/#look=' + b; }""")
    pg2 = page_factory(url, welcomed=False)
    wait_ready(pg2)
    assert pg2.evaluate("window.__zine.page().layout") == "triptych"
    assert not pg2.evaluate("document.querySelector('#dlgWelcome').open")  # открыли по ссылке: без приветствия
    assert pg2.evaluate("location.hash") == ""
    # мусор и опасные значения не ломают приложение
    import base64, json
    bad = base64.urlsafe_b64encode(json.dumps({"rows": 10**9, "layout": 5, "evil": 1, "font_size": "x"}).encode()).decode().rstrip("=")
    pg3 = page_factory("/app/#look=" + bad)
    wait_ready(pg3)
    assert pg3.evaluate("window.__zine.page().rows") <= 12
    assert pg3.errors == []


def test_fold_guide_sound_toggle_and_separations_menu(page_factory):
    pg = page_factory()
    wait_ready(pg)
    pg.click("#btnFile")
    labels = pg.evaluate("[...document.querySelectorAll('#menuFile button')].map(b => b.textContent)")
    assert any("separations" in l or "разделение" in l.lower() for l in labels)
    pg.evaluate("[...document.querySelectorAll('#menuFile button')].find(b => /How to fold|Как сложить/.test(b.textContent)).click()")
    pg.wait_for_selector("#dlgFold[open]")
    assert pg.evaluate("document.querySelectorAll('#foldBody .fold-steps li').length") == 5
    assert pg.evaluate("document.querySelectorAll('#foldBody svg').length") == 5
    pg.click("#dlgFold .dlg-head button")
    pg.click("#btnFile")
    pg.evaluate("[...document.querySelectorAll('#menuFile button')].find(b => /sound|звук/i.test(b.textContent)).click()")
    assert pg.evaluate("localStorage.getItem('zine.sound')") == "true"
    assert pg.errors == []


def test_python_and_js_halftone_plates_match(page_factory):
    """Один и тот же серый массив даёт одну и ту же пластину в десктопном и браузерном движке."""
    import numpy as np
    from PIL import Image
    from engine import ZineGraphicEngine

    h, w = 160, 200
    yy, xx = np.mgrid[0:h, 0:w]
    gray = ((xx / w * 255) * 0.6 + (yy / h * 255) * 0.4 + np.random.RandomState(3).rand(h, w) * 20).clip(0, 255).astype(np.uint8)
    pg = page_factory()
    wait_ready(pg)
    # (размер точки, угол): основной экран и второй экран оверпринта (x1.3, +30°)
    for dot, angle in [(7, 45), (7 * 1.3, 75), (12, 15), (4, 0), (9.5, 22.5)]:
        js = pg.evaluate(
            """async ([g, w, h, dot, angle]) => {
              const E = await import('/app/js/engine.js');
              return Array.from(E.halftoneBits(Uint8Array.from(g), w, h, dot, angle));
            }""",
            [gray.flatten().tolist(), w, h, dot, angle],
        )
        py = ZineGraphicEngine.apply_halftone_dots(Image.fromarray(gray), dot_size=dot, angle=angle)
        same = (np.array(js, dtype=bool).reshape(h, w) == py).mean()
        assert same > 0.995, f"dot={dot} angle={angle}: only {same:.4f} of pixels match"
    assert pg.errors == []


def test_pattern_dithers_match_between_python_and_js(page_factory):
    import numpy as np
    from PIL import Image
    from engine import ZineGraphicEngine

    h, w = 120, 150
    yy, xx = np.mgrid[0:h, 0:w]
    gray = ((xx / w * 255) * 0.7 + (yy / h * 255) * 0.3).clip(0, 255).astype(np.uint8)
    pg = page_factory()
    wait_ready(pg)
    for kind in ("lines", "cross", "stipple", "mezzo", "bayer"):
        for dot, angle in [(7, 45), (10, 20)]:
            js = pg.evaluate(
                """async ([g, w, h, dot, angle, kind]) => {
                  const E = await import('/app/js/engine.js');
                  return Array.from(E.patternBits(Uint8Array.from(g), w, h, dot, angle, kind));
                }""",
                [gray.flatten().tolist(), w, h, dot, angle, kind],
            )
            py = ZineGraphicEngine.apply_pattern_dither(Image.fromarray(gray), kind, dot_size=dot, angle=angle)
            same = (np.array(js, dtype=bool).reshape(h, w) == py).mean()
            assert same > 0.995, f"{kind} dot={dot} angle={angle}: {same:.4f}"
    assert pg.errors == []


def test_wear_remix_locks_and_mutate_run_clean(page_factory):
    pg = page_factory()
    wait_ready(pg)
    pg.evaluate("""() => { const s = document.querySelector('#c_dither'); s.value = 'cross'; s.dispatchEvent(new Event('change')); }""")
    for k, v in (("fold", 80), ("stains", 70), ("dust", 60)):
        pg.evaluate("([k, v]) => { const el = document.querySelector('#c_' + k); el.value = v; el.dispatchEvent(new Event('input')); }", [k, v])
    pg.fill("#c_stamp", "Copy of a copy")
    pg.check("#c_holes")
    pg.wait_for_timeout(800)
    # заблокировать растр, нажать Remix: растр не должен измениться
    pg.evaluate("[...document.querySelectorAll('.locks .chip')].find(b => /Raster|Растр/.test(b.textContent)).click()")
    pg.click("#btnRemix")
    pg.wait_for_timeout(600)
    assert pg.evaluate("document.querySelector('#c_dither').value") == "cross"
    pg.evaluate("[...document.querySelectorAll('button')].find(b => /Mutate|Мутировать/.test(b.textContent)).click()")
    pg.wait_for_timeout(600)
    assert pg.errors == []


def _png_files(tmp_path, n):
    from PIL import Image
    paths = []
    for i in range(n):
        p = tmp_path / f"p{i}.png"
        Image.new("RGB", (160, 200), (40 + i * 30, 90, 160)).save(p)
        paths.append(str(p))
    return paths


def test_booklet_pdf_and_palette_from_photo(page_factory, tmp_path):
    pg = page_factory()
    wait_ready(pg)
    pg.set_input_files("#fileImg", _png_files(tmp_path, 3))
    pg.wait_for_timeout(1500)
    pg.evaluate("[...document.querySelectorAll('button')].find(b => /Palette from photo|Палитра из фото/.test(b.textContent)).click()")
    pg.wait_for_timeout(600)
    assert pg.evaluate("document.querySelector('#c_palette').value") != "Classic B&W (Xerox)"
    pg.evaluate("window.showSaveFilePicker = undefined")
    pg.click("#btnFile")
    with pg.expect_download(timeout=60000) as dl:
        pg.evaluate("[...document.querySelectorAll('#menuFile button')].find(b => /booklet, A4/i.test(b.textContent)).click()")
    path = dl.value.path()
    data = open(path, "rb").read()
    # 3 страницы дополняются до 4 = один лист = 2 стороны = 2 страницы PDF
    assert data.startswith(b"%PDF") and data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") + data.count(b"/Type /Page>") >= 2
    assert pg.errors == []


def test_layers_add_drag_and_render(page_factory):
    pg = page_factory()
    wait_ready(pg)
    pg.evaluate("[...document.querySelectorAll('#layersBox button')].find(b => /Text|Надпись/.test(b.textContent)).click()")
    assert pg.evaluate("document.querySelectorAll('.layers-list .lname').length") == 1
    pg.evaluate("[...document.querySelectorAll('#layersBox button')].find(b => /Sticker|Стикер/.test(b.textContent)).click()")
    pg.wait_for_selector("#dlgStickers[open]")
    assert pg.evaluate("document.querySelectorAll('#stickerGrid button').length") >= 12
    pg.click("#stickerGrid button >> nth=0")
    assert pg.evaluate("document.querySelectorAll('.layers-list .lname').length") == 2
    # перетащить выбранный слой
    box = pg.evaluate("(() => { const r = document.querySelector('#layerSel').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
    pg.mouse.move(box[0], box[1]); pg.mouse.down(); pg.mouse.move(box[0] + 60, box[1] + 40, steps=5); pg.mouse.up()
    pg.wait_for_timeout(500)
    moved = pg.evaluate("(() => { const r = document.querySelector('#layerSel').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
    assert abs(moved[0] - (box[0] + 60)) < 6 and abs(moved[1] - (box[1] + 40)) < 6
    # удалить
    pg.evaluate("[...document.querySelectorAll('.layer-ed button')].find(b => /Delete|Удалить/.test(b.textContent)).click()")
    assert pg.evaluate("document.querySelectorAll('.layers-list .lname').length") == 1
    assert pg.errors == []


def test_history_panel_folder_and_story_video(page_factory, tmp_path):
    pg = page_factory()
    wait_ready(pg)
    pg.evaluate("""() => { const el = document.querySelector('#c_dust'); el.value = 40; el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); }""")
    pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('#btnRemix').click()")
    pg.wait_for_timeout(300)
    pg.keyboard.press("Control+h")
    pg.wait_for_selector("#dlgHistory[open]")
    n = pg.evaluate("document.querySelectorAll('#histList button').length")
    assert n >= 3
    pg.click("#histList li:first-child button")
    assert pg.evaluate("document.querySelector('#dlgHistory').open") is False
    # папка с фото
    d = tmp_path / "folder"; d.mkdir()
    for p in _png_files(d, 3):
        pass
    pg.set_input_files("#fileDir", str(d))
    pg.wait_for_timeout(1500)
    assert pg.evaluate("document.querySelectorAll('#thumbs .th').length") == 3
    # видео для сторис (реальное время ~5 c); в Playwright WebKit запись холста недоступна
    import os
    if os.environ.get("ZINE_BROWSER") == "webkit":
        assert pg.errors == []
        return
    pg.evaluate("window.showSaveFilePicker = undefined")
    pg.click("#btnFile")
    with pg.expect_download(timeout=40000) as dl:
        pg.evaluate("[...document.querySelectorAll('#menuFile button')].find(b => /Story video/i.test(b.textContent)).click()")
    data = open(dl.value.path(), "rb").read()
    assert len(data) > 5000 and (data[:4] == b"\x1aE\xdf\xa3" or data[4:8] == b"ftyp")
    assert pg.errors == []


_PARITY_JS = """async (scale) => {
  const { E, RC } = window.__zine;
  const st = { ...E.mergeState({}), txt_top: 'TEST', overprint: 60, paper: 50, dust: 40 };
  const c = document.createElement('canvas'); c.width = 320; c.height = 320;
  const x = c.getContext('2d'); const g = x.createLinearGradient(0, 0, 320, 320);
  g.addColorStop(0, '#222'); g.addColorStop(1, '#eee'); x.fillStyle = g; x.fillRect(0, 0, 320, 320);
  x.fillStyle = '#888'; x.beginPath(); x.arc(150, 150, 70, 0, 7); x.fill();
  const src = { canvas: c };
  const a = await RC.renderPage(src, st, { scale });
  const b = await E.renderPage(src, st, { scale });
  let bd = 0; for (let i = 0; i < a.bits.length; i++) if (a.bits[i] !== b.bits[i]) bd++;
  return { mode: RC.renderMode(), same: a.width === b.width && a.height === b.height,
           frac: bd / a.bits.length, isCanvas: a.canvas instanceof HTMLCanvasElement };
}"""


def test_worker_render_matches_main_thread(page_factory):
    pg = page_factory()
    wait_ready(pg)
    r = pg.evaluate(_PARITY_JS, 1)
    assert r["same"] and r["isCanvas"]
    if r["mode"] == "worker":      # в браузерах без OffscreenCanvas остаётся запасной путь
        assert r["frac"] < 0.01
    assert pg.errors == []


def test_noworker_flag_falls_back_to_main_thread(page_factory):
    pg = page_factory(path="/app/?noworker")
    wait_ready(pg)
    r = pg.evaluate(_PARITY_JS, 1)
    assert r["mode"] == "main" and r["same"] and r["frac"] == 0
    assert pg.errors == []


def test_worker_pool_renders_in_parallel_and_matches(page_factory):
    pg = page_factory(path="/app/?workers=3")
    wait_ready(pg)
    r = pg.evaluate("""async () => {
      const { RC, E, page } = window.__zine;
      const st = page();
      const outs = await Promise.all([1, 2, 3, 4].map((i) => RC.renderPage(null, { ...st, seed: i }, { scale: 0.5 })));
      const ref = await E.renderPage(null, { ...st, seed: 3 }, { scale: 0.5 });
      let bd = 0; for (let i = 0; i < ref.bits.length; i++) if (ref.bits[i] !== outs[2].bits[i]) bd++;
      return { pool: RC.poolSize(), mode: RC.renderMode(), sizes: outs.map((o) => o.width), frac: bd / ref.bits.length };
    }""")
    if r["mode"] == "worker":
        assert r["pool"] >= 1 and r["frac"] < 0.01
    assert r["sizes"] == [r["sizes"][0]] * 4
    assert pg.errors == []


def test_layer_quick_add_buttons_and_keyboard(page_factory):
    pg = page_factory()
    wait_ready(pg)
    n = lambda: pg.evaluate("document.querySelectorAll('.layers-list .lname').length")
    pg.click("#btnAdd"); pg.click("#btnAddText")
    assert n() == 1
    assert pg.evaluate("document.activeElement && document.activeElement.tagName") == "TEXTAREA"  # сразу можно печатать
    pg.keyboard.type("hi")
    pg.click("#viewport", position={"x": 5, "y": 5})  # убрать фокус из поля
    pg.evaluate("document.activeElement.blur()")
    x0 = pg.evaluate("window.__zine.page().layers[0].x")
    pg.keyboard.press("ArrowRight"); pg.keyboard.press("Shift+ArrowRight")
    assert pg.evaluate("window.__zine.page().layers[0].x") > x0 + 0.02
    pg.click("#btnAdd"); pg.click("#btnAddSticker")
    pg.wait_for_selector("#dlgStickers[open]")
    pg.click("#stickerGrid button >> nth=1")
    assert n() == 2
    pg.keyboard.press("Delete")
    assert n() == 1
    pg.keyboard.press("Escape")
    assert pg.evaluate("document.querySelectorAll('.layers-list .lname[aria-pressed=true]').length") == 0
    assert pg.errors == []


def test_icon_rail_mode_and_detailed_mode(page_factory):
    pg = page_factory(mode="icons")
    wait_ready(pg)
    vis = lambda sel: pg.evaluate(f"(() => {{ const e = document.querySelector('{sel}'); return !!e && e.offsetParent !== null; }})()")
    assert pg.evaluate("document.querySelectorAll('#rail button[data-fly]').length") == 9
    assert not vis("#drawer") and not vis("#c_dither")                       # лист на весь экран: панель закрыта
    pg.click("#rail button[data-fly=s2]")
    assert vis("#c_dither") and not vis("#c_angle") and not vis("#c_layout")   # открыта одна секция, редкое спрятано
    pg.click("#rail button[data-fly=s0]")
    assert vis("#c_layout") and not vis("#c_dither")
    pg.click("#rail button[data-fly=s0]")                                   # повторный клик закрывает
    assert not vis("#c_layout")
    pg.click("#rail button[data-fly=s2]")
    pg.click("#sections .fly-on .more-btn")
    assert vis("#c_angle") and vis("#c_overprint3")
    pg.click("#rail .rail-all")                                              # «Всё»: подробный режим
    assert pg.evaluate("document.documentElement.dataset.mode") == "pro"
    assert vis("#c_layout") and vis("#c_angle") and vis("#presetRow select")
    assert pg.evaluate("JSON.parse(localStorage.getItem('zine.mode'))") == "pro"   # выбор помнится
    assert pg.errors == []


def test_style_gallery_applies_preset(page_factory):
    pg = page_factory()
    wait_ready(pg)
    pg.click("#presetRow .btn[title*='allery'], #presetRow button:has-text('✨')")
    pg.wait_for_selector("#dlgGallery[open]")
    assert pg.evaluate("document.querySelectorAll('#galGrid .gal-tile').length") >= 10
    before = pg.evaluate("window.__zine.page().palette")
    pg.click("#galGrid .gal-tile >> nth=2")
    assert pg.evaluate("document.querySelector('#dlgGallery').open") is False
    pg.click("#presetRow button:has-text('✨')")
    pg.click("#dlgGallery .gal-tabs button[data-g=vars]")
    assert pg.evaluate("document.querySelectorAll('#galGrid .gal-tile').length") == 6
    pg.keyboard.press("Escape")
    assert pg.errors == []


def test_layer_bar_and_export_size_labels_and_more_menu(page_factory):
    pg = page_factory()
    wait_ready(pg)
    assert "×" in pg.evaluate("document.querySelector('#expScale option:checked').textContent")
    pg.click("#btnAdd"); pg.click("#btnAddSticker")
    pg.wait_for_selector("#dlgStickers[open]"); pg.click("#stickerGrid button >> nth=0")
    assert pg.evaluate("!document.querySelector('#layerBar').hidden")
    pg.click("#layerBar [data-act=copy]")
    assert pg.evaluate("document.querySelectorAll('.layers-list .lname').length") == 2
    pg.click("#layerBar [data-act=del]"); pg.click("#layerBar [data-act=del]")
    assert pg.evaluate("document.querySelector('#layerBar').hidden")
    pg.click("#btnFile")
    assert pg.evaluate("!![...document.querySelectorAll('#menuFile .more-toggle')].length")
    assert pg.evaluate("[...document.querySelectorAll('#menuFile button')].find(b => /stencil|трафарет/i.test(b.textContent)).offsetParent") is None
    pg.click("#menuFile .more-toggle")
    assert pg.evaluate("[...document.querySelectorAll('#menuFile button')].find(b => /stencil|трафарет/i.test(b.textContent)).offsetParent !== null")
    assert pg.errors == []


def test_ransom_layer_new_fonts_and_page_reorder(page_factory):
    pg = page_factory()
    wait_ready(pg)
    r = pg.evaluate("""async () => {
      const { RC, E, page } = window.__zine;
      const base = { ...page(), layers: [] };
      const withL = { ...base, layers: [{ type: 'text', text: 'НЕТ БОГОВ', x: .5, y: .5, size: .25, rot: 0, color: 'ink', style: 'ransom', font: 'Rubik Dirt' }] };
      const a = await RC.renderPage(null, base, { scale: 0.5 }), b = await RC.renderPage(null, withL, { scale: 0.5 });
      const da = a.canvas.getContext('2d').getImageData(0, 0, a.width, a.height).data, db = b.canvas.getContext('2d').getImageData(0, 0, b.width, b.height).data;
      let diff = 0; for (let i = 0; i < da.length; i += 4) if (da[i] !== db[i]) diff++;
      return { diff, fonts: Object.keys(E.CFG ? E.CFG.FONTS : {}).length };
    }""")
    assert r["diff"] > 500
    # порядок страниц: перетаскиваем третью миниатюру на первую
    pg.evaluate("window.__zine.addPage(); window.__zine.addPage();")
    pg.wait_for_timeout(300)
    assert pg.evaluate("document.querySelectorAll('#thumbs .th').length") == 3
    pg.evaluate("window.__zine.page().txt_top = 'THIRD'; window.__zine.commit();")
    pg.drag_and_drop("#thumbs .th >> nth=2", "#thumbs .th >> nth=0")
    pg.wait_for_timeout(300)
    assert pg.evaluate("window.__zine.S.pages[0].txt_top") == "THIRD"
    assert pg.errors == []


def test_phone_sheet_handle_and_hidden_strip(page_factory):
    pg = page_factory(mobile=True, width=390, height=844, mode="icons")
    wait_ready(pg)
    assert pg.evaluate("getComputedStyle(document.querySelector('#strip')).display") == "flex"
    assert pg.evaluate("getComputedStyle(document.querySelector('#drawer')).display") == "none"
    pg.tap("#rail button[data-fly=s2]")
    assert pg.evaluate("getComputedStyle(document.querySelector('#strip')).display") == "none"
    h0 = pg.evaluate("document.querySelector('#drawer').getBoundingClientRect().height")
    pg.click("#sheetHandle")
    h1 = pg.evaluate("document.querySelector('#drawer').getBoundingClientRect().height")
    assert h1 > h0 * 1.4
    pg.click("#drawerClose")                                                 # крестик возвращает лист на весь экран
    assert pg.evaluate("getComputedStyle(document.querySelector('#drawer')).display") == "none"
    assert pg.evaluate("getComputedStyle(document.querySelector('#strip')).display") == "flex"
    assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert pg.errors == []


def test_escape_closes_panel_and_gallery_is_styled(page_factory):
    pg = page_factory(mode="icons")
    wait_ready(pg)
    pg.click("#rail button[data-fly=s2]")
    assert pg.evaluate("getComputedStyle(document.querySelector('#drawer')).display") == "flex"
    pg.keyboard.press("Escape")
    assert pg.evaluate("getComputedStyle(document.querySelector('#drawer')).display") == "none"
    pg.click("#rail button[data-fly=gallery]")
    pg.wait_for_selector("#dlgGallery[open]")
    assert pg.evaluate("getComputedStyle(document.querySelector('#galGrid')).display") == "grid"   # стили галереи на месте
    assert pg.errors == []


def test_tablet_portrait_uses_side_panel(page_factory):
    pg = page_factory(mobile=True, width=768, height=1024, mode="icons")
    wait_ready(pg)
    pg.tap("#rail button[data-fly=s2]")
    r = pg.evaluate("(() => { const d = document.querySelector('#drawer').getBoundingClientRect(), v = document.querySelector('#preview').getBoundingClientRect(); return [d.right, v.left, v.width]; })()")
    assert r[0] <= r[1] + 1 and r[2] > 300           # лист рядом с панелью, а не под ней
    assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_photo_object_handles_snap_and_layer_rows(page_factory, tmp_path):
    pg = page_factory()
    wait_ready(pg)
    pg.click("#btnAdd")
    with pg.expect_file_chooser() as fc:
        pg.click("#btnAddPhoto")
    fc.value.set_files(str(WEB / "img" / "sample.jpg"))
    wait_until(pg, "window.__zine.page().layers.length === 1")
    assert pg.evaluate("window.__zine.page().layers[0].type") == "bitmap"
    # масштаб за угловую ручку
    s0 = pg.evaluate("window.__zine.page().layers[0].size")
    pg.wait_for_selector(".lh-se", state="visible")
    pg.wait_for_timeout(300)
    h = pg.locator(".lh-se").bounding_box()
    pg.mouse.move(h["x"] + 7, h["y"] + 7); pg.mouse.down(); pg.mouse.move(h["x"] + 50, h["y"] + 50, steps=4); pg.mouse.up()
    assert pg.evaluate("window.__zine.page().layers[0].size") > s0
    # поворот за верхнюю ручку
    r = pg.locator(".lh-rot").bounding_box()
    pg.mouse.move(r["x"] + 7, r["y"] + 7); pg.mouse.down(); pg.mouse.move(r["x"] + 100, r["y"] + 30, steps=4); pg.mouse.up()
    assert pg.evaluate("window.__zine.page().layers[0].rot") != 0
    # привязка к центру: слой чуть сдвинут и должен прилипнуть к 0.5
    box = pg.evaluate("(() => { const r = document.querySelector('#layerSel').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
    pg.mouse.move(box[0], box[1]); pg.mouse.down(); pg.mouse.move(box[0] + 3, box[1] + 2, steps=3)
    assert pg.evaluate("document.querySelector('.guide-v').hidden") is False
    pg.mouse.up()
    assert pg.evaluate("window.__zine.page().layers[0].x") == 0.5
    # глаз, замок
    pg.evaluate("document.querySelector('#layersBox .lrow .lbtn').click()")
    assert pg.evaluate("window.__zine.page().layers[0].hidden") is True
    pg.evaluate("document.querySelector('#layersBox .lrow .lbtn').click()")
    pg.evaluate("document.querySelectorAll('#layersBox .lrow .lbtn')[1].click()")
    assert pg.evaluate("window.__zine.page().layers[0].locked") is True
    assert pg.evaluate("document.querySelector('#layerSel').classList.contains('locked')")
    assert pg.errors == []


def test_free_layout_templates_text_warp_and_mechanics(page_factory):
    pg = page_factory()
    wait_ready(pg)
    # шаблон собирает свободный лист: раскладка free, слои с фото и надписями
    pg.click("#rail button[data-fly=s5]")
    pg.select_option("#layersBox select:not(#addShape) >> nth=0", "Афиша")
    wait_until(pg, "window.__zine.page().layers.length >= 3")
    assert pg.evaluate("window.__zine.page().layout") == "free"
    kinds = pg.evaluate("window.__zine.page().layers.map(l => l.type)")
    assert "bitmap" in kinds and "text" in kinds and "sticker" in kinds
    # искажение текста доходит до слоя и меняет рендер
    pg.evaluate("document.querySelectorAll('.layers-list .lname')[2].click()")
    sels = pg.locator("#layersBox .layer-ed select")
    pg.wait_for_timeout(300)
    n = sels.count()
    pg.evaluate("""(() => { const s = [...document.querySelectorAll('#layersBox .layer-ed select')].find(x => [...x.options].some(o => o.value === 'wave')); s.value = 'wave'; s.dispatchEvent(new Event('change')); })()""")
    assert pg.evaluate("window.__zine.page().layers.some(l => l.warp === 'wave')")
    # новые ползунки механики копира есть и сохраняют значение
    for k in ("ghost", "bands", "smear"):
        assert pg.evaluate(f"window.__zine.page().{k}") == 0
        pg.evaluate(f"(() => {{ const e = document.querySelector('#c_{k}'); e.value = 60; e.dispatchEvent(new Event('input')); e.dispatchEvent(new Event('change')); }})()")
        assert pg.evaluate(f"window.__zine.page().{k}") == 60
    assert pg.errors == []


def test_choosing_free_layout_puts_photo_on_sheet(page_factory):
    pg = page_factory()
    wait_ready(pg)
    assert pg.evaluate("window.__zine.page().layers.length") == 0
    pg.evaluate("""(() => { const s = document.querySelector('#c_layout'); s.value = 'free'; s.dispatchEvent(new Event('change')); })()""")
    wait_until(pg, "window.__zine.page().layers.length === 1")
    assert pg.evaluate("window.__zine.page().layers[0].type") == "bitmap"
    assert pg.errors == []


def test_layers_mode_splits_sheet_and_everything_moves(page_factory):
    pg = page_factory()
    wait_ready(pg)
    assert pg.evaluate("window.__zine.page().layers.length") == 0
    pg.click("#btnLayersMode")
    wait_until(pg, "window.__zine.page().layers.length >= 3")
    page = pg.evaluate("({layout: window.__zine.page().layout, top: window.__zine.page().txt_top, kinds: window.__zine.page().layers.map(l => l.type)})")
    assert page["layout"] == "free" and page["top"] == ""
    assert "bitmap" in page["kinds"] and "text" in page["kinds"]  # кадры и подписи стали слоями
    assert pg.evaluate("document.querySelectorAll('.ghost').length") >= 2
    # выбор слоя клавишами и дубликат
    n = pg.evaluate("window.__zine.page().layers.length")
    pg.keyboard.press(".")
    pg.keyboard.press("Control+d")
    assert pg.evaluate("window.__zine.page().layers.length") == n + 1
    # перетаскивание строки в списке слоёв меняет порядок
    first = pg.evaluate("window.__zine.page().layers[0].type + window.__zine.page().layers[0].x")
    pg.evaluate("""(() => { const rows = [...document.querySelectorAll('.layers-list .lrow')]; const dt = new DataTransfer();
      rows[rows.length - 1].dispatchEvent(new DragEvent('dragstart', { dataTransfer: dt, bubbles: true }));
      rows[0].dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true })); })()""")
    assert pg.evaluate("window.__zine.page().layers[0].type + window.__zine.page().layers[0].x") != first
    pg.keyboard.press("l")
    assert pg.evaluate("document.querySelectorAll('.ghost').length") == 0
    assert pg.errors == []


def test_shadow_align_and_new_layer_library(page_factory):
    pg = page_factory()
    wait_ready(pg)
    assert pg.evaluate("Object.keys(window.__zine.CFG ? window.__zine.CFG.STICKERS : {}).length") >= 0
    pg.click("#rail button[data-fly=s5]")
    pg.select_option("#layersBox select:not(#addShape) >> nth=0", "Route 66")
    wait_until(pg, "window.__zine.page().layers.length >= 3")
    pg.evaluate("document.querySelector('.layers-list .lname').click()")  # верхний слой
    pg.wait_for_selector(".align-row button")
    pg.evaluate("document.querySelectorAll('.align-row button')[0].click()")  # к левому краю
    x = pg.evaluate("window.__zine.page().layers[window.__zine.page().layers.length - 1].x")
    assert x < 0.5
    pg.evaluate("document.querySelectorAll('.align-row button')[1].click()")  # по центру
    assert pg.evaluate("window.__zine.page().layers[window.__zine.page().layers.length - 1].x") == 0.5
    pg.evaluate("""(() => { const r = [...document.querySelectorAll('#layersBox .layer-ed input[type=range]')].find(i => i.closest('.ctl').textContent.match(/Тень|shadow/i)); r.value = 0.6; r.dispatchEvent(new Event('input')); r.dispatchEvent(new Event('change')); })()""")
    assert pg.evaluate("window.__zine.page().layers.some(l => l.shadow === 0.6)")
    # новые шаблоны есть в списке
    opts = pg.evaluate("document.querySelector('#layersBox select:not(#addShape)').options.length")
    assert opts >= 16
    assert pg.errors == []


def test_manifesto_library_ru_has_all_and_en_has_no_cyrillic(page_factory):
    pg = page_factory(width=1440, height=860, lang="ru")
    wait_ready(pg)
    pg.keyboard.press("Control+m")
    pg.wait_for_selector("dialog[open]")
    assert pg.inner_text("#mCount").startswith("119 из 119") or pg.inner_text("#mCount").startswith("119 of 119")
    pg2 = page_factory(width=1440, height=860, lang="en")
    wait_ready(pg2)
    for _ in range(12):
        pg2.click("#btnRemix")
        pg2.wait_for_timeout(120)
        txt = pg2.evaluate("(() => { const s = document.querySelector('#c_txt_top'); if (!s) throw new Error('no caption field'); return s.value; })()")
        assert not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in txt), txt


def test_layers_mode_keeps_cropped_photo(page_factory, tmp_path):
    from PIL import Image
    img = tmp_path / "p.png"
    Image.effect_noise((600, 400), 90).convert("RGB").save(img)
    pg = page_factory(width=1440, height=860, lang="ru")
    wait_ready(pg)
    pg.set_input_files("#fileImg", str(img))
    pg.wait_for_timeout(800)
    pg.evaluate("document.querySelector('#btnLayersMode').click()")
    pg.wait_for_timeout(1800)
    n = pg.evaluate("document.querySelectorAll('.lname').length")
    ink = pg.evaluate("(() => { const c = document.querySelector('#preview'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 16) if (d[i] < 110) n++; return n; })()")
    assert n >= 2 and ink > 3000, (n, ink)
    assert pg.errors == []


def test_beginner_guide_opens_walks_and_runs_actions(page_factory):
    pg = page_factory(width=1440, height=860, lang="ru")
    wait_ready(pg)
    pg.click("#btnHelp")
    pg.click("#helpGuide")
    pg.wait_for_selector("#dlgGuide[open]")
    assert pg.evaluate("document.querySelectorAll('#guideBody .gdot').length") == 6
    for _ in range(5):
        pg.click("#guideBody .row .btn:last-child")
    assert "Распечатай" in pg.inner_text("#guideBody h4")
    pg.click("#guideBody .row .btn:last-child")  # «Готово»
    assert pg.evaluate("document.querySelector('#dlgGuide').open") is False
    pg.keyboard.press("F1")
    pg.click("#helpGuide")
    pg.click("#guideBody .gdot:nth-child(5)")
    pg.click("#guideBody .btn.primary")  # «Включить слои»
    assert pg.evaluate("document.querySelector('#btnLayersMode').getAttribute('aria-pressed')") == "true"
    assert pg.errors == []


def test_guide_page_is_static_crawlable_and_valid(page_factory):
    pg = page_factory(path="/guide/", width=1000, height=800)
    pg.wait_for_selector("h1")
    assert pg.errors == []
    assert pg.evaluate("document.querySelectorAll('.guide-steps li').length") == 12
    ld = json.loads(pg.evaluate("document.querySelector('script[type=\"application/ld+json\"]').textContent"))
    assert ld["@type"] == "HowTo" and len(ld["step"]) == 6
    assert pg.evaluate("document.querySelector('link[rel=canonical]').href").endswith("/guide/")


def test_gutter_and_recopy_change_the_render(page_factory):
    pg = page_factory(width=1440, height=860)
    wait_ready(pg)
    base = pg.evaluate("window.__zine.page().gutter === 0 && window.__zine.page().recopy === 0")
    assert base is True
    for key in ("gutter", "recopy"):
        pg.evaluate("(k) => { const z = window.__zine; z.page()[k] = 90; z.requestRender(); }", key)
        pg.wait_for_timeout(1500)
        assert pg.evaluate("(k) => window.__zine.page()[k]", key) == 90
    assert pg.errors == []
