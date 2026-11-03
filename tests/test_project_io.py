import json
import os
import zipfile

import numpy as np
import pytest

import config
import project_io


def _pages(n=2):
    return [dict(config.DEFAULT_STATE, img="img1", txt_top=f"страница {i}") for i in range(n)]


def test_roundtrip(tmp_path):
    path = str(tmp_path / "p.zine")
    img = np.random.default_rng(1).integers(0, 255, (40, 30, 3), dtype=np.uint8)
    project_io.write_project(path, _pages(), {"img1": img, "unused": img}, 1)
    pages, images, cur = project_io.read_project(path)
    assert len(pages) == 2 and cur == 1
    assert pages[0]["txt_top"] == "страница 0"
    assert set(images) == {"img1"}  # неиспользуемые фото в проект не попадают
    assert np.array_equal(images["img1"], img)


def test_write_is_atomic_and_leaves_no_tmp(tmp_path):
    path = str(tmp_path / "p.zine")
    project_io.write_project(path, _pages(1), {}, 0)
    good = open(path, "rb").read()
    with pytest.raises(Exception):
        project_io.write_project(path, [{"img": None, "bad": object()}], {}, 0)
    assert open(path, "rb").read() == good  # прежний файл не испорчен
    assert not os.path.exists(path + ".tmp")


def test_numpy_values_are_serialised(tmp_path):
    path = str(tmp_path / "p.zine")
    page = dict(config.DEFAULT_STATE, rows=np.int64(5), tilt=np.float64(1.5))
    project_io.write_project(path, [page], {}, 0)
    assert project_io.read_project(path)[0][0]["rows"] == 5


def test_legacy_single_image_format(tmp_path):
    import cv2
    path = str(tmp_path / "old.zine")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"pages": [{"layout": "reference_columns"}], "cur": 0}))
        zf.writestr("source.png", cv2.imencode(".png", np.zeros((10, 10, 3), np.uint8))[1].tobytes())
    pages, images, _ = project_io.read_project(path)
    assert pages[0]["img"] == "legacy" and "legacy" in images


@pytest.mark.parametrize("payload", [b"not a zip", b""])
def test_broken_file_raises(tmp_path, payload):
    path = str(tmp_path / "bad.zine")
    open(path, "wb").write(payload)
    with pytest.raises(Exception):
        project_io.read_project(path)


def test_zip_without_manifest_or_pages(tmp_path):
    path = str(tmp_path / "x.zine")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("hello.txt", "x")
    with pytest.raises(ValueError):
        project_io.read_project(path)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"pages": []}))
    with pytest.raises(ValueError):
        project_io.read_project(path)
