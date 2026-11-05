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
