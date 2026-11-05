# Changelog

## 2.2.2
- **Phones: scrolling no longer moves sliders.** On touch screens a slider only moves when you grab its handle; touching anywhere else on the track scrolls the panel.

## 2.2.1
- Fixed the style gallery (browser) that lost its styling in 2.1.0: tiles, tabs and grid look right again.

## 2.2.0
- **Desktop app redesign, same layout as the browser.** A ribbon of icon tiles on the left (Styles, Photo, Grid, Frames, Toner, Colour, Wear, Layers, Text, All) opens one slide-out panel with a single settings section; the ✕ or a second click closes it and the sheet gets the whole window. *All* shows every setting in one list as before, *Styles* drops down the preset menu. Save PNG, Remix, Fit, 1:1 and export scale now float over the sheet, and the page controls moved into the page strip header. The last open panel is remembered. Adding a layer opens the Layers panel.

## 2.1.1
- **Worn stickers.** Stickers no longer look cleaner than the rest of the sheet: toner dropouts, faded patches and scratches are eroded into them (browser and desktop use the same formulas).

## 2.1.0
- **Browser app redesign: the sheet fills the whole screen.** Tools float over it instead of sitting in columns. A ribbon of icon "stickers" opens one slide-out panel at a time (left side on desktop, bottom on phones, same behaviour everywhere); the ✕ or a second tap on the icon puts the sheet back on the full screen. The All icon shows every setting in one list. Add / Before-after / Fit / PNG float over the sheet, pages live in a bottom strip, and the sheet always re-fits to the free space.
- **New look.** Black header with an acid underline, halftone stage, paper panels with hard shadows and dotted title bars, tilted ribbon tiles, lifted active page. Both the paper and dark themes.
- **Phone.** Landscape phones get a compact side ribbon; portrait phones get a bottom ribbon, a drag handle on the panel and one row of floating buttons above the sheet.
- The desktop (Tkinter) app is unchanged; it will follow the same section order later.

## 2.0.0
- **Underground kit.** 12 new stickers (skull, anarchy, COPY, DIY, safety pin, no sign, crown, dead face, cassette, peace, warning, vinyl); a *ransom note* text backing where each letter sits on its own paper scrap in its own font, size and tilt (browser and desktop draw it the same way); five underground fonts with Cyrillic (Rubik Dirt, Distressed, Wet Paint, Spray Paint, Glitch); five new presets (Dirty Punk, Spray Wall, Glitch Tape, Wet Paint, Copy of a Copy of a Copy). Layer fonts are now loaded before rendering, so a chosen font no longer falls back on first use.
- **Phone layout.** The settings panel has a drag handle to make it taller, the page strip hides while a panel is open (more room for the sheet), theme and language moved into the File menu on phones.
- **Pages.** Drag thumbnails to reorder pages (mouse; touch keeps the arrow buttons).
- **Desktop:** a backing selector for text layers (box, tape, outline, ransom note).
- Together with 1.4–1.7: render workers, free layers, icon rail and detailed mode, style gallery, realistic stains.

## 1.7.0
- **Style gallery (browser).** The ✨ button (and the Styles icon) shows every ready style rendered on your own photo; click a tile to apply it. A second tab shows six random variations (respecting Remix locks), with "six more" for another batch.
- **Two panel modes (browser).** *Icons* (default): a slim rail of icons on the side, each opens one settings section next to the sheet, rare sliders are tucked under "More settings". *Detailed*: every setting in one list, as before. The choice is remembered.
- **Less clutter above the sheet.** Text, sticker and caption placing are in one "＋ Add" menu; "Before/after" and the zoom label shrink on phones; export scale shows the final size (for example 2× · 2000×3000); rare export formats sit under "More formats & tools" in the File menu.
- **Layer bar.** When a layer is selected, a small bar over the sheet offers edit, duplicate, bring to front and delete.

## 1.6.0
- **Layers are easier to reach.** Browser: two buttons above the sheet (＋Aa, ＋✦) add a text or a sticker straight away; a new text is selected for typing right away; double-click a text on the sheet to edit it; Delete removes the selected layer, arrow keys nudge it (Shift = bigger step), Esc deselects.
- **Desktop: drag layers with the mouse** right on the preview, with a dashed frame around the selected layer and a "move" cursor over layers. Click outside a layer still pans the sheet.

## 1.5.1
- Fix: with several render workers, two renders of the same photo started together could fail with "source missing". Use this build instead of 1.5.0.

## 1.5.0
- **Browser: several render workers.** Exporting a book (ZIP of pages, PDF) renders neighbouring pages in parallel while the previous one is being written. On a 2-core machine six 2x pages take 3.5 s instead of 6.1 s. Up to 3 workers on desktop, 1 on phones (memory). `?workers=N` overrides it.

## 1.4.2
- **Stains look real now** (both versions): coffee leaves an uneven ring with a dark rim and a few splashes around it, grease is a soft translucent spot. They are multiplied onto the sheet, so paper and ink show through.

## 1.4.1
- **Browser: page rendering moved to a Web Worker.** Big renders (export, ink separations, booklet) no longer freeze the interface; the preview stays responsive while a 3x sheet is being built. The result is identical to the old main-thread path (checked pixel by pixel). Browsers without OffscreenCanvas fall back to the old path automatically; `?noworker` forces it.

## 1.4.0
- **Free layers** (both versions): any number of text blocks and stickers on a page, each with its own position, size, rotation, colour and order. In the browser you drag them on the sheet; the desktop app has a layer list with sliders. 16 vector stickers (star, burst, arrow, smiley, eye, bolt, heart, scissors, cross, spiral, scribble ring, barcode, flower, bubble, target, asterisk).
- **Three and four inks** (both versions): a third ink for midtones and a fourth for highlights, each with its own screen angle and misregistration. Ink separations export all plates.
- **History panel** (browser, Ctrl+H): every step with a short description; click to jump back.
- **Folder of photos** (browser, also desktop booklet and calibration): add a whole folder, each photo becomes a page.
- **Story video** (browser): a 9:16 clip of the sheet coming out of the copier, with the copier sound if it is on.
- **Five bundled fonts:** Rubik Mono One, Press Start 2P, Marck Script (with Cyrillic), Special Elite and Permanent Marker (Latin only).
- **Desktop:** saddle-stitch booklet (A4 / Letter) and printer calibration sheet, Remix locks, new wear effects.

## 1.3.0
- **Five new screens** (both versions): lines, cross-hatch, stipple, mezzotint, Bayer. Python and JS give the same plate (tested).
- **Sheet wear** (both versions): fold crease, punch holes, coffee and grease stains, dust and hairs, and a rubber stamp with your own text.
- **Remix locks and Mutate:** keep palette, layout, raster, text, font or wear while remixing; Mutate nudges the numeric settings a little.
- **Four new presets:** Line Engraving, Mezzotint, Dirty Office, Bayer 8-bit (20 in total). New 4:5 Instagram canvas.
- **Browser:** saddle-stitch booklet PDF for any page count (A4 or Letter, correct page order for double-sided printing), printer calibration sheet, palette from the current photo.
- Landing page copy rewritten.

## 1.2.0
- **Riso ink separations** (both versions): ZIP with one 1-bit plate per ink, corner registration crosses and a README with ink colours and print order.
- **Fold guide:** illustrated 5-step guide to folding the 8-page mini-zine, printable from the app.
- **Copier sound** (browser, off by default) and a short "print ritual" animation when an export finishes (respects reduced motion).
- **Desktop:** copier sound on export (File menu toggle, Windows).
- Author's manifesto and a screen-recording demo on the landing page and README.
- Releases are automatic: bump `APP_VERSION` in `config.py` and push to `main`; CI builds the exe, installer and zip and publishes release `<version>`.
- Tests: Python and JS halftone plates are checked pixel for pixel on the same input.

## 1.1.0
The tool gets deeper, and the browser gets a version of it.

- **Browser version** (`web/`): the full studio in vanilla JavaScript — no install, works offline as a PWA, phone and
  tablet layouts, touch pan / pinch, IndexedDB autosave. Same presets, manifestos and `.zine` format as the Windows app
  (files round-trip both ways). Exports PNG, ZIP, 1-bit PNG, PDF, A4 PDF and the 8-page mini-zine.
- **New effects** (both versions): paper texture (fibre, blotches, edge vignette), riso overprint (second halftone
  screen on another angle with its own ink colour) and masking tape strips that are photocopied with the page.
- **New presets:** Riso Overprint and Tape Collage (nine built-in in total).
- Old projects without the new keys render exactly as before.
- **Manifesto library grew from 30 to 54** built-in English manifestos; new categories COPIER, DIY and CITY. Both versions have “Write your own” in the library (two lines of text, saved under “Mine”).
- **13 frame layouts instead of 4** (both versions, identical geometry, covered by a Python-vs-JS test): column on the right, diagonal cascade, overlapping pile, two columns, mosaic, diptych, triptych, ribbon, full page.
- **Seven new presets** for the new layouts (16 in total): Diagonal Punk, Photo Pile, Newsprint Mosaic, Cyanotype Triptych, Full-page Poster, Film-test Ribbon, Riso Diptych.
- **Share a look:** File → “Copy link to this look” makes a URL carrying the style, caption and seed (never the photo); whoever opens it gets the same look on their own photo. Links are validated on load.
- **Copier lamp:** a light bar sweeps across the sheet when you switch style or remix.
- **Before / after** comparison with a draggable divider in the browser editor.
- **Browser editor redesign:** light “paper” theme by default (dark one on the ◐ button), first-run welcome dialog
  (add a photo / take a photo / play with the sample), Share and Copy-to-clipboard in the File menu.
- **Accessibility and phones:** touch targets of at least 44 px, labelled fields, a heading and image role for the
  canvas, no horizontal overflow down to 320 px wide, notifications no longer cover the page strip.
- Content-Security-Policy on the site and the app (no inline scripts, no third-party requests).
- Landing page redesigned as a zine; gallery covers all nine presets.
- Repository: MIT licence, English README (+ Russian), `tools/` to regenerate web config and offline cache,
  `tests/test_web_sync.py`, GitHub Actions for tests, site deployment and tagged releases.

## 1.0.1
Исправление запуска на других компьютерах.

- В exe вшиты библиотеки Visual C++ (`msvcp140.dll` и др.). Без них на чистом Windows не загружался OpenCV, и программа
  не открывалась.
- `build.py` проверяет, что эти библиотеки есть в сборке, и прерывает сборку, если их нет.
- Если запуск всё же не удался, программа показывает окно с причиной и ссылкой на Visual C++ Redistributable;
  подробности пишутся в `crash.log`.

## 1.0.0
Первый релиз.

- Движок: рабочий полутоновый растр, 4 раскладки (шахматка, колонка, контактный лист, герой + копии),
  потеря качества «копии с копии», рваные края, ризографская приводка, 9 палитр + своя, 6 шрифтов.
- Страницы: свои фото, кадр и стиль у каждой страницы; пакетная загрузка фото; порядок страниц.
- Библиотека манифестов (Ctrl+M): 30 готовых английских по 5 категориям, поиск, предпросмотр, «раздать по
  страницам», свои манифесты («Мои»).
- Пресеты стиля: 7 встроенных, свои пресеты, «применить ко всем страницам».
- Фото страницы: поворот на 90° и зеркало; эффект «тень края копира».
- Экспорт: PNG (1×–3×), все страницы в PNG, PDF без потерь, PDF для печати A4, мини-зин на 8 страниц
  (A4, верная раскладка сгиба), 1-bit трафарет.
- Проекты `.zine` с атомарной записью, автосохранение и восстановление после сбоя, отмена и возврат,
  запрос о сохранении при выходе.
- Перетаскивание фото и `.zine` в окно, открытие файла при запуске.
- Журнал ошибок, настройки, поддержка HiDPI.
- Сборка одной командой (`python build.py`), самотест exe, установщик Inno Setup, GitHub Actions.
