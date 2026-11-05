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
    g = engine.ZineGraphicEngine()
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
    g = engine.ZineGraphicEngine()
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
