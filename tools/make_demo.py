"""Records a short demo of the browser app (Playwright) and converts it to docs/demo.mp4 + docs/demo.gif.
Usage: python tools/make_demo.py path/to/photo.jpg   (needs playwright + ffmpeg)"""
import functools, http.server, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
photo = sys.argv[1]
tmp = Path(tempfile.mkdtemp())


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "web")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/app/"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1100, "height": 700}, record_video_dir=str(tmp), record_video_size={"width": 1100, "height": 700})
    ctx.add_init_script("localStorage.setItem('zine.lang','en');localStorage.setItem('zine.welcomed','1');localStorage.setItem('zine.theme','\"paper\"');")
    pg = ctx.new_page()
    pg.goto(url); pg.wait_for_timeout(1200)
    pg.set_input_files("#fileImg", photo); pg.wait_for_timeout(1800)
    names = pg.evaluate("[...document.querySelectorAll('#presetRow select option')].map(o => o.value).filter(Boolean)")
    for n in names[8:16]:
        pg.select_option("#presetRow select", n); pg.wait_for_timeout(1300)
    pg.evaluate("[...document.querySelectorAll('#layersBox button')].find(b => /Sticker/.test(b.textContent)).click()")
    pg.click("#stickerGrid button >> nth=1"); pg.wait_for_timeout(1200)
    pg.evaluate("[...document.querySelectorAll('#layersBox button')].find(b => /Text/.test(b.textContent)).click()"); pg.wait_for_timeout(1000)
    for _ in range(3):
        pg.evaluate("[...document.querySelectorAll('button')].find(b => /Mutate/.test(b.textContent)).click()"); pg.wait_for_timeout(1000)
    pg.click("#btnCompare"); pg.wait_for_timeout(1200)
    pg.mouse.click(500, 350); pg.wait_for_timeout(900)
    pg.click("#btnCompare"); pg.wait_for_timeout(600)
    vid = pg.video.path()
    ctx.close(); b.close()

out = ROOT / "docs"
shutil.copy(vid, tmp / "raw.webm")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "raw.webm"), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30", "-vf", "scale=1000:-2", str(out / "demo.mp4")], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "raw.webm"), "-vf", "fps=8,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer", str(out / "demo.gif")], check=True)
print("ok", os.path.getsize(out / "demo.mp4"), os.path.getsize(out / "demo.gif"))
