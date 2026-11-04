import functools
import http.server
import threading
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[2] / "web"
pw = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")


@pytest.fixture(scope="session")
def base_url():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

    handler = functools.partial(Quiet, directory=str(WEB))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # браузер не установлен: python -m playwright install chromium
            pytest.skip(f"Chromium is not available: {e}")
        yield b
        b.close()


@pytest.fixture
def page_factory(browser, base_url):
    """Открывает страницу; собирает ошибки консоли (включая нарушения CSP)."""
    made = []

    def make(path="/app/", mobile=False, width=1280, height=800, welcomed=True, lang="en"):
        kw = {"viewport": {"width": width, "height": height}}
        if mobile:
            kw = dict(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = browser.new_context(accept_downloads=True, **kw)
        init = f"localStorage.setItem('zine.lang','{lang}');"
        if welcomed:
            init += "localStorage.setItem('zine.welcomed','1');"
        ctx.add_init_script(init)
        pg = ctx.new_page()
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
        pg.goto(base_url + path)
        made.append(ctx)
        return pg

    yield make
    for c in made:
        c.close()


def wait_ready(pg, timeout=20000):
    """Опрос через evaluate: wait_for_function использует eval, а у приложения строгий CSP."""
    import time
    end = time.time() + timeout / 1000
    while time.time() < end:
        if pg.evaluate("window.__ready === true"):
            return
        pg.wait_for_timeout(100)
    raise AssertionError("приложение не стало готовым: " + "; ".join(pg.errors))
