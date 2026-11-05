import imposition
from engine import ZineGraphicEngine


def test_booklet_order_matches_saddle_stitch():
    assert imposition.booklet_sides(8) == [(7, 0), (1, 6), (5, 2), (3, 4)]
    assert imposition.booklet_sides(5) == [(7, 0), (1, 6), (5, 2), (3, 4)]  # добивка пустыми до 8
    assert imposition.booklet_sides(4) == [(3, 0), (1, 2)]


def test_every_page_appears_once():
    for n in (1, 4, 7, 12, 16):
        flat = [p for side in imposition.booklet_sides(n) for p in side]
        assert sorted(flat) == list(range(-(-n // 4) * 4))


def test_calibration_sheet_is_a4_300dpi():
    img = imposition.calibration_sheet(ZineGraphicEngine())
    assert img.size == (2480, 3508)
