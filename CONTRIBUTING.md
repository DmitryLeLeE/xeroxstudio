# Contributing

Ideas, presets, manifestos and bug reports are welcome.

```
pip install -r requirements.txt pytest
python -m pytest -q tests          # engine, presets, projects, PDF, web sync (+ browser tests if Playwright is installed)
python -m http.server -d web 8000  # try the browser version at http://localhost:8000/app/
```

- Rendering constants live in `config.py` / `presets.py` / `manifestos.py`. The web app reads a **generated**
  `web/app/js/config.js`: run `python tools/gen_config_js.py` after changing them, and `python tools/gen_sw.py`
  after changing any file under `web/`. The test suite fails if either is stale.
- The same preset must look the same in Python and in JavaScript (`engine.py` ↔ `web/app/js/engine.js`).
- Manifestos are English, uppercase, two parts (top / bottom), 2 lines at most each.
- Keep the browser version dependency-free (no bundler, no CDN).
