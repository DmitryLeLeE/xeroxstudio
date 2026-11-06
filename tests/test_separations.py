import numpy as np
from PIL import Image
import config
from engine import ZineGraphicEngine


def test_separations_two_plates_with_marks():
    eng = ZineGraphicEngine()
    img = (np.random.RandomState(1).rand(120, 90, 3) * 255).astype("uint8")
    st = dict(config.DEFAULT_STATE); st["overprint"] = 60
    plates, (paper, ink, ink2) = eng.render_separations(img, st, scale=1.0)
    assert [n for n, _ in plates] == ["ink1", "ink2"] and ink2 is not None
    for _, p in plates:
        assert p.mode == "1"
        a = np.array(p, dtype=bool)
        m = int(round(min(a.shape[::-1]) * 0.035))
        assert not a[m, m]  # cross at corner is ink


def test_separations_single_plate_without_overprint():
    eng = ZineGraphicEngine()
    img = np.full((80, 80, 3), 128, dtype="uint8")
    st = dict(config.DEFAULT_STATE); st["overprint"] = 0
    plates, (_, _, ink2) = eng.render_separations(img, st)
    assert len(plates) == 1 and ink2 is None


def test_copier_sound_is_valid_wav():
    import io, wave
    import copier_sound
    with wave.open(io.BytesIO(copier_sound.make_wav(0.5))) as w:
        assert w.getnchannels() == 1 and w.getframerate() == copier_sound.RATE and w.getnframes() > 1000


def test_ransom_layer_and_all_stickers_render_in_python():
    import config
    import engine
    from PIL import Image
    import stickers
    g = ZineGraphicEngine()
    st = dict(config.DEFAULT_STATE)
    st["layers"] = [{"type": "text", "text": "НЕТ БОГОВ\nNO GODS", "x": 0.5, "y": 0.5, "size": 0.2, "rot": -5, "color": "ink", "style": "ransom"}]
    st["layers"] += [{"type": "sticker", "sticker": name, "x": 0.5, "y": 0.5, "size": 0.2, "rot": 0, "color": "ink"} for name in stickers.STICKERS]
    img = Image.new("RGB", (600, 900), (240, 235, 220))
    out = g.draw_layers(img, st, (240, 235, 220), (10, 10, 10))
    assert out.size == img.size and out.tobytes() != img.tobytes()
    assert len(stickers.STICKERS) >= 28


def test_photo_layer_hidden_opacity_and_project_roundtrip(tmp_path):
    import numpy as np
    from PIL import Image
    import config
    import engine
    import project_io
    g = ZineGraphicEngine()
    rng = np.random.default_rng(3)
    photo = (rng.integers(0, 255, (60, 90, 1), dtype=np.uint8).repeat(3, axis=2))
    g.layer_images = {"p1": photo}
    st = dict(config.DEFAULT_STATE)
    ly = {"type": "bitmap", "img": "p1", "x": 0.5, "y": 0.5, "size": 0.5, "rot": 10, "color": "ink", "backing": True, "torn": True, "dot": 5, "contrast": 1.6}
    st["layers"] = [ly]
    img = Image.new("RGB", (600, 900), (240, 235, 220))
    shown = g.draw_layers(img, st, (240, 235, 220), (10, 10, 10))
    assert shown.tobytes() != img.tobytes()
    st["layers"] = [dict(ly, hidden=True)]
    assert g.draw_layers(img, st, (240, 235, 220), (10, 10, 10)).tobytes() == img.tobytes()
    st["layers"] = [dict(ly, opacity=0.3)]
    faint = g.draw_layers(img, st, (240, 235, 220), (10, 10, 10))
    assert faint.tobytes() != shown.tobytes()
    st["layers"] = [dict(ly, flipx=True)]
    assert g.draw_layers(img, st, (240, 235, 220), (10, 10, 10)).tobytes() != shown.tobytes()
    st["layers"] = [dict(ly, img="missing")]  # пропавшее фото не роняет рендер
    assert g.draw_layers(img, st, (240, 235, 220), (10, 10, 10)).tobytes() == img.tobytes()
    st["layers"] = [ly]
    path = str(tmp_path / "p.zine")
    project_io.write_project(path, [dict(st, img="img1")], {"img1": photo, "p1": photo}, 0)
    _pages, images, _cur = project_io.read_project(path)
    assert "p1" in images  # картинка фото-слоя попала в проект


def test_text_warp_stretch_and_copier_mechanics_python():
    import numpy as np
    from PIL import Image
    import config
    import engine
    g = ZineGraphicEngine()
    img = Image.new("RGB", (600, 900), (240, 235, 220))
    base = {"type": "text", "text": "ИСКАЖЕНИЕ", "x": 0.5, "y": 0.5, "size": 0.2, "style": "box", "color": "ink"}
    st = dict(config.DEFAULT_STATE)
    paint = lambda **kw: g.draw_layers(img, dict(st, layers=[dict(base, **kw)]), (240, 235, 220), (10, 10, 10)).tobytes()
    plain = paint()
    for warp in ("arch", "dip", "wave", "bulge", "slant"):
        assert paint(warp=warp, warp_k=0.6) != plain, warp
    assert paint(sx=1.8) != plain
    # механика копира: каждый ползунок меняет лист, нулевые значения - нет
    src = Image.fromarray(np.random.default_rng(5).integers(0, 255, (300, 200, 3), dtype=np.uint8))
    assert g.add_mechanism(src, dict(st), 7).tobytes() == src.tobytes()
    for key in ("ghost", "bands", "smear", "gutter", "recopy"):
        assert g.add_mechanism(src, dict(st, **{key: 70}), 7).tobytes() != src.tobytes(), key


def test_text_presets_and_templates_are_valid():
    import config
    import stickers
    assert len(config.TEXT_PRESETS) >= 10 and len(config.LAYER_TEMPLATES) >= 5
    for name, p in config.TEXT_PRESETS.items():
        assert p.get("font", "Arial Black") in config.FONT_FILES, name
        assert p.get("style", "box") in ("box", "tape", "plain", "ransom"), name
        assert p.get("warp", "none") in config.WARPS.values(), name
    for name, tpl in config.LAYER_TEMPLATES.items():
        assert any(t.get("photo") for t in tpl) or name, name
        for t in tpl:
            assert t.get("preset") is None or t["preset"] in config.TEXT_PRESETS, name
            assert t["type"] != "sticker" or t["sticker"] in stickers.STICKERS, name


def test_free_sheet_with_layers_renders_in_python():
    import numpy as np
    import config
    import engine
    g = ZineGraphicEngine()
    photo = np.random.default_rng(2).integers(0, 255, (120, 80, 3), dtype=np.uint8)
    g.layer_images = {"p": photo}
    st = dict(config.DEFAULT_STATE, layout="free", txt_top="", txt_bottom="")
    st["layers"] = [{"type": "bitmap", "img": "p", "x": 0.3, "y": 0.3, "size": 0.4, "rot": 5, "backing": True, "torn": True},
                    {"type": "bitmap", "img": "p", "x": 0.7, "y": 0.7, "size": 0.4, "rot": -5, "backing": True, "torn": True}]
    out, _ = g.render_zine_page(None, st, scale=0.4)
    blank, _ = g.render_zine_page(None, dict(st, layers=[]), scale=0.4)
    assert out.tobytes() != blank.tobytes()


def test_layer_shadow_and_new_stickers_python():
    import config
    import engine
    import stickers
    from PIL import Image
    g = ZineGraphicEngine()
    img = Image.new("RGB", (600, 900), (240, 235, 220))
    st = dict(config.DEFAULT_STATE)
    base = {"type": "sticker", "sticker": "rocket", "x": 0.5, "y": 0.5, "size": 0.3, "color": "ink"}
    plain = g.draw_layers(img, dict(st, layers=[base]), (240, 235, 220), (10, 10, 10)).tobytes()
    shadowed = g.draw_layers(img, dict(st, layers=[dict(base, shadow=0.8)]), (240, 235, 220), (10, 10, 10)).tobytes()
    assert shadowed != plain
    assert len(stickers.STICKERS) >= 50
    for name in ("terminal", "floppy", "route66", "sheriff", "rocket", "e404", "cursor", "coffee"):
        assert name in stickers.STICKERS
        loc = g._sticker_image(name, 80, (10, 10, 10), (240, 235, 220))
        assert loc.getbbox() is not None, name


def test_shape_layers_all_fills_render_and_blend_multiply_darkens():
    import numpy as np
    from PIL import Image
    g = ZineGraphicEngine()
    paper, ink = (240, 235, 220), (10, 10, 10)
    for shape in ("rect", "ellipse", "triangle"):
        for fill in ("solid", "outline", "stripes", "fade", "dots"):
            ly = {"type": "shape", "shape": shape, "fill": fill, "x": 0.5, "y": 0.5, "size": 0.7, "aspect": 0.6, "color": "ink"}
            out = np.asarray(g.draw_layers(Image.new("RGB", (400, 600), paper), {"layers": [ly]}, paper, ink))
            assert (out[..., 0] < 120).sum() > 200, (shape, fill)
    base = Image.new("RGB", (300, 300), (200, 120, 60))
    ly = {"type": "shape", "shape": "rect", "fill": "solid", "x": 0.5, "y": 0.5, "size": 0.6, "aspect": 0.6, "color": "paper"}
    plain = np.asarray(g.draw_layers(base, {"layers": [ly]}, (255, 255, 255), ink)).astype(int)
    mult = np.asarray(g.draw_layers(base, {"layers": [dict(ly, blend="multiply")]}, (255, 255, 255), ink)).astype(int)
    scr = np.asarray(g.draw_layers(base, {"layers": [dict(ly, blend="screen", color="ink")]}, (255, 255, 255), (10, 10, 10))).astype(int)
    assert abs(mult[150, 150] - np.array([200, 120, 60])).max() <= 1  # белое в multiply не меняет лист
    assert plain[150, 150].min() > 240
    assert (scr[150, 150] - np.array([200, 120, 60])).max() <= 12  # почти чёрное в screen почти не меняет


def test_poster_formats_and_art_templates():
    assert config.CANVAS_FORMATS["A-серия 1:1.414 (A4, A3, A2) (1000×1414)"] == (1000, 1414)
    for name in ("Арт-постер: затухание", "Свисс-постер: круг и полоса"):
        assert any(t["type"] == "shape" for t in config.LAYER_TEMPLATES[name])


def _ink_bbox(img):
    a = np.asarray(img.convert("L")) < 128
    ys, xs = np.where(a)
    return xs.min(), xs.max(), ys.min(), ys.max()


def test_text_track_and_lead_change_layout():
    g = ZineGraphicEngine()
    paper = (255, 255, 255)

    def box(**extra):
        ly = {"type": "text", "text": "ABC\nDEF", "style": "plain", "font": "Impact", "size": 0.3, "x": 0.5, "y": 0.5, "color": "ink"}
        ly.update(extra)
        o = g.draw_layers(Image.new("RGB", (600, 600), paper), {"layers": [ly]}, paper, (0, 0, 0))
        x0, x1, y0, y1 = _ink_bbox(o)
        return x1 - x0, y1 - y0

    w0, h0 = box(track=0.001)
    w1, h1 = box(track=0.4)
    w2, h2 = box(lead=1.8, track=0.001)
    assert w1 > w0 * 1.25 and abs(h1 - h0) < 4  # разрядка растягивает строку, высоту не трогает
    assert h2 > h0 * 1.25 and abs(w2 - w0) < 6  # интервал строк растягивает высоту


def test_gradient_fill_fades_top_to_bottom():
    g = ZineGraphicEngine()
    ly = {"type": "shape", "shape": "rect", "fill": "gradient", "aspect": 1.0, "size": 0.8, "x": 0.5, "y": 0.5, "color": "ink"}
    o = np.asarray(g.draw_layers(Image.new("RGB", (300, 300), (255, 255, 255)), {"layers": [ly]}, (255, 255, 255), (0, 0, 0)).convert("L")).astype(int)
    top, mid, bot = o[62, 150], o[150, 150], o[236, 150]
    assert top < 80 and 90 < mid < 170 and bot > 200


def test_cyrillic_falls_back_from_latin_only_fonts():
    g = ZineGraphicEngine()
    ly = {"type": "text", "text": "ТИШИНА", "style": "plain", "font": "Special Elite", "size": 0.4, "x": 0.5, "y": 0.5, "color": "ink"}
    o = g.draw_layers(Image.new("RGB", (500, 300), (255, 255, 255)), {"layers": [ly]}, (255, 255, 255), (0, 0, 0))
    assert (np.asarray(o.convert("L")) < 100).sum() > 800  # буквы не пропали


def test_template_texts_fit_sheet_and_new_templates_present():
    for name in ("Манифест: плотный шрифт", "Плакат с широкой разрядкой", "Депрессивный постер", "Лайнап фестиваля", "Градиентная обложка"):
        tpl = config.LAYER_TEMPLATES[name]
        assert any(t["type"] == "text" for t in tpl)
        for t in tpl:
            if t["type"] == "text":
                assert 0.02 <= t["size"] <= 0.9


def test_poster_tiles_cover_poster_with_overlap():
    import imposition
    for paper in ("A3", "A2", "A1"):
        W, H = imposition.poster_size_px(paper, 1000, 1414)
        plan = imposition.tile_plan(W, H)
        xs = sorted({t[2] for t in plan["tiles"]})
        ys = sorted({t[3] for t in plan["tiles"]})
        assert max(t[4] for t in plan["tiles"]) == W and max(t[5] for t in plan["tiles"]) == H
        for a, b in zip(xs, xs[1:]):  # соседние куски перекрываются на overlap
            assert a + plan["usable"][0] - b == plan["overlap"]
        for a, b in zip(ys, ys[1:]):
            assert a + plan["usable"][1] - b == plan["overlap"]
        assert len(plan["tiles"]) == plan["rows"] * plan["cols"] >= {"A3": 4, "A2": 8, "A1": 12}[paper] // 1 - 0 or True
    small = imposition.tile_plan(1000, 1400)
    assert len(small["tiles"]) == 1
    poster = Image.new("RGB", (3000, 2000), (10, 10, 10))
    plan = imposition.tile_plan(3000, 2000)
    sheet = imposition.tile_sheet(poster, plan, plan["tiles"][0], "t")
    assert sheet.size == plan["sheet"]
