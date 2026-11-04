# Changelog

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
