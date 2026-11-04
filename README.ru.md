# Xerox Zine Studio

[English](README.md) · **Русский**

Генератор ксерокс-зинов: полутон, рваные края, потеря качества «копии с копии», ризо-наложение,
фактура бумаги, скотч, многостраничные проекты, экспорт в PNG, PDF, мини-зин A4 и 1-bit трафарет.
Есть версия для **Windows** (Python/Tkinter) и версия **в браузере** (папка [`web/`](web), работает на телефоне и офлайн):
https://dmitrylelee.github.io/xeroxstudio/

![Страница приложения](docs/gallery.jpg)

## Веб-версия

Папка `web/` — отдельное приложение на чистом JavaScript без сборки и зависимостей. Те же пресеты, манифесты и
формат `.zine`. Чтобы открыть локально: `python -m http.server -d web 8000` и `http://localhost:8000/`.
После изменения `config.py`/`presets.py` выполните `python tools/gen_config_js.py`, после изменения файлов сайта —
`python tools/gen_sw.py` (обновляет офлайн-кэш). Тест `tests/test_web_sync.py` проверяет, что файлы актуальны.

## Запуск из исходников

```
pip install -r requirements.txt
python main.py                # можно передать путь к .zine или к фото
```

Фото и `.zine` можно просто перетащить в окно.

## Сборка exe одной командой

```
python build.py               # dist\XeroxZineStudio.exe (один файл)
python build.py --onedir      # папка + zip: быстрее старт, реже ложные срабатывания антивируса
python build.py --installer   # + установщик dist\XeroxZineStudio-Setup-<версия>.exe (нужен Inno Setup 6:
                              #   winget install JRSoftware.InnoSetup)
```

(или двойной клик по `build.bat`). Скрипт сам ставит зависимости, рисует иконку, гоняет тесты,
собирает exe и проверяет его встроенным самотестом `XeroxZineStudio.exe --selftest out.json`.
Если проверка не пройдена, сборка считается неудачной.

Нужен Python 3.11–3.13 с tkinter. Сборка делается на Windows, чтобы получился Windows-exe.

## Релиз через GitHub

`.github/workflows/build.yml` собирает exe, zip и установщик на Windows по тегу `v*` (или вручную из вкладки
Actions) и кладёт их в артефакты. Версия берётся из `config.APP_VERSION`: поднимите её и `CHANGELOG.md`
перед тегом.

## Если программа не открывается на другом компьютере

1. Передавайте **весь** результат сборки: один файл `XeroxZineStudio.exe` или, для `--onedir`, всю папку (zip) целиком.
   Из папки `XeroxZineStudio` одиночный exe без `_internal` работать не будет.
2. Windows защитник/SmartScreen: «Windows защитила ваш компьютер» → «Подробнее» → «Выполнить в любом случае».
   Если файл скачан из интернета или мессенджера: правый клик → «Свойства» → галочка «Разблокировать».
   Антивирус мог удалить одиночный exe: надёжнее `--onedir`/установщик либо подпись файла сертификатом.
3. Нужна 64-разрядная Windows 10 или новее. Если появилось окно с ошибкой про DLL, установите
   [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe). Начиная с версии 1.0.1 нужные
   библиотеки уже внутри программы, но на «N»-редакциях Windows и Windows Server может понадобиться
   Media Feature Pack.
4. Подробности ошибки: `%LOCALAPPDATA%\XeroxZineStudio\crash.log` и `app.log`. Пришлите их при обращении.

## Тесты

```
python -m pytest -q tests
```

## Лицензия

[MIT](LICENSE). Лицензии компонентов: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Где лежат данные

`%LOCALAPPDATA%\XeroxZineStudio\`: `app.log` (журнал ошибок), `settings.json` (последние папки,
масштаб экспорта), `presets.json` и `manifestos.json` (ваши пресеты и манифесты), `autosave.zine` (автосохранение каждые 2 минуты; предлагается восстановить, если программа
закрылась аварийно). Журнал открывается из меню «Справка».

## Файлы проекта

| Файл | Назначение |
|---|---|
| `launcher.py` | точка входа exe: понятное окно, если запуск не удался |
| `main.py` | окно, страницы, отмена, экспорт, самотест |
| `engine.py` | рендер страницы: раскладки, растр, палитра, текст |
| `ui_components.py` | тема, холст предпросмотра, рамка кадра, слайдеры |
| `project_io.py` | чтение и атомарная запись `.zine` |
| `pdf_writer.py` | PDF без потерь (Flate вместо JPEG) |
| `presets.py` | встроенные и пользовательские пресеты стиля |
| `manifestos.py`, `manifest_dialog.py` | библиотека манифестов и окно выбора |
| `assets/` | каскад Хаара для поиска лиц (не зависит от версии OpenCV) |
| `installer.iss` | установщик Inno Setup (ассоциация `.zine`) |
| `THIRD_PARTY_NOTICES.md`, `CHANGELOG.md` | лицензии и история версий |
| `appdata.py` | папка данных, настройки, журнал |
| `config.py` | форматы, палитры, манифесты, состояние по умолчанию |
| `make_icon.py` | рисует `icon.ico` и `icon.png` движком программы |
| `build.py`, `build.bat`, `zine_studio.spec` | сборка |

Если Windows Defender или антивирус ругается на одиночный exe от PyInstaller, это известное ложное
срабатывание: используйте `--onedir` или подпишите файл сертификатом.
