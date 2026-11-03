import numpy as np
import pytest
from PIL import Image

import config
from engine import ZineGraphicEngine


@pytest.fixture(scope="module")
def engine():
    return ZineGraphicEngine()


@pytest.fixture(scope="module")
def photo():
    yy, xx = np.mgrid[0:300, 0:240]
    g = (255 * (1 - np.hypot((xx - 120) / 100, (yy - 150) / 130))).clip(0, 255).astype(np.uint8)
    return np.dstack([g, g, g])


def test_halftone_makes_dots_not_stripes(engine):
    ramp = Image.fromarray(np.tile(np.linspace(0, 255, 400, dtype=np.uint8), (200, 1)))
    bits = engine.apply_halftone_dots(ramp, dot_size=8)
    assert bits.dtype == bool
    # на горизонтальной рампе и по строкам, и по столбцам должны чередоваться чёрное и белое
    assert 0.3 < bits.mean() < 0.7
    assert len({tuple(r) for r in bits[:40, 100:200]}) > 10  # строки различаются: это точки, а не полосы


@pytest.mark.parametrize("layout", list(config.LAYOUTS.values()))
@pytest.mark.parametrize("dither", list(config.DITHERS.values()))
def test_render_layouts_and_dithers(engine, photo, layout, dither):
    img, bits = engine.render_zine_page(photo, {"layout": layout, "dither": dither, "txt_top": "ТЕСТ\nTEST"}, scale=0.4)
    assert img.size == (400, 600)
    assert bits.mode == "1"


def test_only_palette_colors_and_no_uninitialised_pixels(engine, photo):
    img, _ = engine.render_zine_page(photo, {"palette": "Acid Cyberpunk (Neon Lime / Black)", "misreg": 5})
    colors = np.unique(np.asarray(img).reshape(-1, 3), axis=0)
    assert len(colors) <= 3  # бумага, краска, «призрак» приводки


def test_deterministic_for_same_seed_and_scale_changes_size(engine, photo):
    st = {"seed": 7, "noise": 40}
    a, _ = engine.render_zine_page(photo, st, scale=0.5)
    b, _ = engine.render_zine_page(photo, st, scale=0.5)
    assert np.array_equal(np.asarray(a), np.asarray(b))
    c, _ = engine.render_zine_page(photo, st, scale=1.0)
    assert c.size == (1000, 1500)


def test_works_without_photo_and_with_every_format(engine):
    for fmt, (w, h) in config.CANVAS_FORMATS.items():
        img, _ = engine.render_zine_page(None, {"format": fmt}, scale=0.25)
        assert img.size == (int(w * 0.25), int(h * 0.25))


def test_out_size_for_mini_zine(engine, photo):
    img, _ = engine.render_zine_page(photo, {}, out_size=(877, 1240))
    assert img.size == (877, 1240)


def test_long_text_does_not_crash_and_old_layout_alias(engine, photo):
    st = {"txt_top": "ОЧЕНЬ ДЛИННАЯ СТРОКА " * 12, "font_size": 120, "layout": "reference_columns"}
    img, _ = engine.render_zine_page(photo, st, scale=0.5)
    assert img.size == (500, 750)


def test_outline_text_with_fractional_bbox_does_not_crash(engine, photo):
    # регресс: Impact + контур давал дробные размеры плашки и падал в Image.new
    st = {"txt_top": "WHO WATCHES\nTHE OBSERVER?", "tstyle": "outline", "font": "Impact", "font_size": 60, "text_align": "right"}
    img, _ = engine.render_zine_page(photo, st, scale=0.5)
    assert img.size == (500, 750)


def test_copier_edge_darkens_left_and_bottom_only(engine, photo):
    base, _ = engine.render_zine_page(photo, {"copier_edge": 0, "noise": 0, "streaks": 0, "misreg": 0, "layout": "column"})
    edged, _ = engine.render_zine_page(photo, {"copier_edge": 100, "noise": 0, "streaks": 0, "misreg": 0, "layout": "column"})
    b, e = np.asarray(base.convert("L")), np.asarray(edged.convert("L"))
    assert e[:, :8].mean() < b[:, :8].mean() - 60       # левая кромка заметно темнее
    assert e[-6:, :].mean() < b[-6:, :].mean() - 60      # нижняя тоже
    assert abs(float(e[200:1200, 600:900].mean()) - float(b[200:1200, 600:900].mean())) < 1  # центр не тронут
