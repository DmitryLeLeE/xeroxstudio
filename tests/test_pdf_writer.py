import numpy as np
import pytest
from PIL import Image

import pdf_writer

pypdf = pytest.importorskip("pypdf")


def _page(seed, size=(120, 90)):
    rng = np.random.default_rng(seed)
    arr = np.zeros((size[1], size[0], 3), np.uint8)
    arr[:] = (250, 247, 238)
    arr[rng.random(arr.shape[:2]) < 0.3] = (10, 10, 10)
    arr[rng.random(arr.shape[:2]) < 0.05] = (255, 42, 133)
    return Image.fromarray(arr)


def test_pdf_is_valid_and_lossless(tmp_path):
    path = str(tmp_path / "a.pdf")
    pages = [_page(1), _page(2, (80, 120))]
    assert pdf_writer.write_pdf(path, iter(pages), dpi=300.0) == 2
    reader = pypdf.PdfReader(path)
    assert len(reader.pages) == 2
    box = reader.pages[0].mediabox
    assert abs(float(box.width) - 120 * 72 / 300) < 0.01
    for src, page in zip(pages, reader.pages):
        got = np.asarray(page.images[0].image.convert("RGB"))
        assert np.array_equal(got, np.asarray(src))  # ни одного изменённого пикселя


def test_many_colours_fall_back_to_rgb(tmp_path):
    path = str(tmp_path / "b.pdf")
    noise = Image.fromarray(np.random.default_rng(3).integers(0, 255, (60, 60, 3), dtype=np.uint8))
    pdf_writer.write_pdf(path, [noise])
    got = np.asarray(pypdf.PdfReader(path).pages[0].images[0].image.convert("RGB"))
    assert np.array_equal(got, np.asarray(noise))


def test_empty_pdf_is_rejected_and_leaves_no_file(tmp_path):
    path = tmp_path / "c.pdf"
    with pytest.raises(ValueError):
        pdf_writer.write_pdf(str(path), [])
    assert not path.exists() and not (tmp_path / "c.pdf.tmp").exists()
