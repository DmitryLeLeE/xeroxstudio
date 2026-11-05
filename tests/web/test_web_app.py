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
    assert pg.evaluate("document.querySelectorAll('.layers-list button').length") == 1
    pg.evaluate("[...document.querySelectorAll('#layersBox button')].find(b => /Sticker|Стикер/.test(b.textContent)).click()")
    pg.wait_for_selector("#dlgStickers[open]")
    assert pg.evaluate("document.querySelectorAll('#stickerGrid button').length") >= 12
    pg.click("#stickerGrid button >> nth=0")
    assert pg.evaluate("document.querySelectorAll('.layers-list button').length") == 2
    # перетащить выбранный слой
    box = pg.evaluate("(() => { const r = document.querySelector('#layerSel').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
    pg.mouse.move(box[0], box[1]); pg.mouse.down(); pg.mouse.move(box[0] + 60, box[1] + 40, steps=5); pg.mouse.up()
    pg.wait_for_timeout(500)
    moved = pg.evaluate("(() => { const r = document.querySelector('#layerSel').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
    assert abs(moved[0] - (box[0] + 60)) < 6 and abs(moved[1] - (box[1] + 40)) < 6
    # удалить
    pg.evaluate("[...document.querySelectorAll('.layer-ed button')].find(b => /Delete|Удалить/.test(b.textContent)).click()")
    assert pg.evaluate("document.querySelectorAll('.layers-list button').length") == 1
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
    n = lambda: pg.evaluate("document.querySelectorAll('.layers-list button').length")
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
    assert pg.evaluate("document.querySelectorAll('.layers-list button[aria-pressed=true]').length") == 0
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
    pg.wait_for_function("document.querySelectorAll('#galGrid .gal-tile').length >= 10") if False else None
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
    assert pg.evaluate("document.querySelectorAll('.layers-list button').length") == 2
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
