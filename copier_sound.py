"""Звук копира для экспорта: синтезируется в памяти (шум + щелчок лампы), играет только в Windows."""
import io
import wave

import numpy as np

RATE = 22050


def make_wav(duration=1.5, seed=7):
    """WAV (16 бит, моно) как bytes: полосовой шум, растущий по частоте, и щелчок в начале."""
    rng = np.random.default_rng(seed)
    n = int(RATE * duration)
    t = np.arange(n) / RATE
    noise = rng.uniform(-1, 1, n)
    # скользящее среднее разной ширины даёт «шипение» с растущей яркостью
    smooth = np.convolve(noise, np.ones(8) / 8, mode="same")
    mix = np.where(t < duration * 0.35, smooth, noise * 0.6 + smooth * 0.4)
    env = np.minimum(1.0, t / 0.12) * np.minimum(1.0, (duration - t) / 0.45)
    click = np.sign(np.sin(2 * np.pi * 90 * t)) * np.exp(-t / 0.03) * (t < 0.1)
    sig = (mix * env * 0.28 + click * 0.25).clip(-1, 1)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((sig * 32767).astype("<i2").tobytes())
    return buf.getvalue()


def play():
    """Проиграть асинхронно; на других системах и при ошибках ничего не делает."""
    try:
        import winsound
        winsound.PlaySound(make_wav(), winsound.SND_MEMORY | winsound.SND_ASYNC)
    except Exception:
        pass
