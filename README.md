<div align="center">

# Xerox Zine Studio

**Turn photos into photocopied zine pages.**<br>
Halftone · torn edges · generation loss · riso overprint · paper grain · tape

[**Open in the browser →**](https://dmitrylelee.github.io/xeroxstudio/app/) · [Landing page](https://dmitrylelee.github.io/xeroxstudio/) · [Download for Windows](https://github.com/DmitryLeLeE/xeroxstudio/releases/latest)

English · [Русский](README.ru.md)

![One photo, nine presets](docs/gallery.jpg)

![Screen recording: one photo, eight looks](docs/demo.gif)

</div>

I saw real people's photocopied and riso work on Instagram and wanted to make that at home, without any equipment.
So this is a tool that turns a photo into a copied, crooked, slightly dirty page. Print it, fold it, cut along the red
line, give it to someone. It comes in two versions with the same looks and the same project file:

| | Web | Windows |
|---|---|---|
| Where | any modern browser, phone / tablet / desktop | Python 3.11–3.13 + Tkinter, `.exe` |
| Install | none; optional PWA, works offline | `python build.py` or a release download |
| Source | [`web/`](web) (vanilla JS, no build step) | repository root |
| Photos | processed locally, never uploaded | processed locally |

![The web app](docs/app-web.jpg)

## What it does

- **Real halftone.** Amplitude screen with angle and dot size, Floyd–Steinberg grain, hard 1-bit stencil, lines, cross-hatch, stipple, mezzotint, Bayer, toner noise, scanner streaks, copier edge shadow, ink misregistration.
- **Riso overprint.** A second ink layer on another screen angle, shifted and multiplied over the first. Nine paper / ink pairs plus your own colours.
- **Paper and tape.** Fibre and blotch texture, edge vignette, torn tape strips that get photocopied along with the page.
- **Generation loss.** 13 layouts (staggered, columns, diagonal cascade, overlapping pile, mosaic, diptych, triptych, ribbon, contact sheet, hero + copies, full page…); every next copy is blurrier and harsher.
- **Layers.** Any number of texts and 28 vector stickers per page (skull, anarchy, COPY, DIY, cassette…), draggable in both versions. A *ransom note* backing cuts every letter from a different paper scrap. Third and fourth ink for 3–4 colour prints.
- **Underground fonts.** Rubik Dirt, Distressed, Wet Paint, Spray Paint and Glitch (all with Cyrillic), plus the older bundled set.
- **Sheet-first layout.** The sheet fills the screen; a ribbon of icons opens one slide-out panel at a time (left on desktop, bottom on phones, same in the desktop app); Esc or ✕ closes it, *All* lists every setting.
- **Style gallery.** Every preset rendered on your own photo, plus six random variations; click one to apply (browser).
- **Sheet wear.** Fold crease, punch holes, stains, dust and a stamp with your own text. Remix has locks, Mutate nudges a look.
- **Booklet.** Saddle-stitch PDF for any page count (A4 / Letter) and a printer calibration sheet (browser).
- **Ink separations.** Export per-ink 1-bit plates with registration crosses (ZIP) to print on a real risograph.
- **Fold guide.** Illustrated how to fold the 8-page mini-zine, printable from the app.
- **Manifestos.** 54 built-in English manifestos in eight categories, search, your own texts, three backings (box, Dymo tape, outline), draggable caption.
- **Faces.** Optional black bar over the eyes and sticker cut-outs (Haar cascade; runs in-browser too).
- **Print-ready.** PNG up to 3×, book PDF, A4 PDF with margins, **8-page mini-zine** with fold and cut lines, 1-bit PNG for stencil printing.
- **Projects.** `.zine` files (a zip with `manifest.json` and PNGs) open in both versions. Autosave, undo / redo.
- **25 presets.** Dirty Punk, Spray Wall, Glitch Tape, Wet Paint, Copy of a Copy of a Copy, Classic Xerox, Newsprint, Acid Riot, Punk Flyer, Cyanotype, 35 mm Contact Sheet, Night Vision, Riso Overprint, Tape Collage, Diagonal Punk, Photo Pile, Newsprint Mosaic, Cyanotype Triptych, Full-page Poster, Film-test Ribbon, Riso Diptych, Line Engraving, Mezzotint, Dirty Office, Bayer 8-bit, or save your own.
- **Share a look.** One link carries a style and caption (no photo), so anyone can try it on their own picture.
- **Before / after.** Drag a divider across the sheet to compare with the original photo (browser version).

## Run it

**Browser:** <https://dmitrylelee.github.io/xeroxstudio/app/> — or locally:

```
python -m http.server -d web 8000     # then open http://localhost:8000/app/
```

**Windows, from source:**

```
pip install -r requirements.txt
python main.py                  # optionally pass a .zine or a photo
```

**Build the exe** (on Windows):

```
python build.py                 # dist\XeroxZineStudio.exe, tests + self-test included
python build.py --onedir        # folder + zip: faster start, fewer antivirus false positives
python build.py --installer     # + Inno Setup installer (winget install JRSoftware.InnoSetup)
```

To release: bump `APP_VERSION` in `config.py` (and `installer.iss`), run `python tools/gen_config_js.py`, push to `main`. GitHub Actions builds the exe, zip and installer and publishes release `<version>` automatically (a `v*` tag works too).

## Project layout

```
engine.py  presets.py  config.py  manifestos.py   rendering core, presets, constants, manifesto library
main.py  ui_components.py  manifest_dialog.py     Tkinter interface
project_io.py  pdf_writer.py                      .zine files, own PDF writer
web/                                              the browser version (landing at /, app at /app/)
tools/gen_config_js.py  tools/gen_sw.py           keep web/ in sync with the Python constants, rebuild offline cache
tests/  tests/web/                                pytest suite (engine, presets, projects, PDF, web sync) and Playwright browser tests
docs/                                             screenshots and the .zine format
```

The web app reads its constants from `web/app/js/config.js`, which is **generated** from `config.py`, `presets.py`
and `manifestos.py`. After changing any of them run `python tools/gen_config_js.py`; after changing any site file run
`python tools/gen_sw.py`. `pytest` fails if either is stale.

## Tests

```
python -m pytest -q tests                      # browser tests are skipped without Playwright
pip install playwright && python -m playwright install chromium   # to run tests/web too
```

## Changelog and licenses

See [CHANGELOG.md](CHANGELOG.md). Code is [MIT](LICENSE); bundled fonts (SIL OFL) and the face model (Intel
licence) are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The sample portrait is a NASA photograph
(public domain).
