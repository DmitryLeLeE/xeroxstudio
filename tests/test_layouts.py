import numpy as np
import pytest

import config
from engine import ZineGraphicEngine

SIZES = [(1000, 1500), (1200, 1200), (1080, 1920)]


def test_layout_list_has_fourteen():
    assert len(config.LAYOUTS) == 14 and len(set(config.LAYOUTS.values())) == 14


@pytest.mark.parametrize("layout", sorted(v for v in config.LAYOUTS.values() if v != "free"))
@pytest.mark.parametrize("rows", [1, 2, 4, 6, 8])
@pytest.mark.parametrize("size", SIZES)
def test_boxes_are_valid_and_mostly_on_page(layout, rows, size):
    cw, ch = size
    boxes = ZineGraphicEngine._layout_boxes(layout, cw, ch, rows, 12, 1.0)
    assert boxes, layout
    for x, y, w, h in boxes:
        assert w > 4 and h > 4, (layout, rows, (x, y, w, h))
        assert x >= 0 and y >= 0, (layout, rows, (x, y, w, h))
        assert x + w <= cw + 1 and y + h <= ch + 12 + ch // rows, (layout, rows, (x, y, w, h))


@pytest.mark.parametrize("layout", sorted(config.LAYOUTS.values()))
def test_every_layout_renders(layout):
    eng = ZineGraphicEngine()
    img = np.random.default_rng(1).integers(0, 255, (300, 400, 3), dtype=np.uint8)
    st = {**config.DEFAULT_STATE, "layout": layout, "rows": 4, "txt_top": "A", "txt_bottom": "B"}
    out, _ = eng.render_zine_page(img, st, scale=0.3)
    assert out.size[0] > 100 and out.size[1] > 100


def test_free_layout_has_no_frames_and_renders_blank_paper():
    assert ZineGraphicEngine._layout_boxes("free", 1000, 1500, 4, 12, 1.0) == []
    eng = ZineGraphicEngine()
    out, _bits = eng.render_zine_page(None, dict(config.DEFAULT_STATE, layout="free"), scale=0.3)
    assert out.size[0] > 100
