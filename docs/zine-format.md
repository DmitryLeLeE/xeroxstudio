# `.zine` project format

A `.zine` file is an ordinary zip archive written by both the Windows and the browser version
(`project_io.py` / `web/app/js/io.js`).

```
project.zine
├── manifest.json
└── images/
    ├── <key>.png     one PNG per source photo (pages reference photos by key)
    └── ...
```

`manifest.json`:

| Key | Meaning |
|---|---|
| `version` | format version, currently `2` |
| `pages` | non-empty list; each item is the full style state of one page (keys as in `DEFAULT_STATE` in `config.py`: preset values, texts, crop, `seed`, …) and `img`, the key of its photo (or null for the built-in sample) |
| `cur` | index of the page that was selected |
| `images` | keys of the photos stored in `images/` |

Colours are `[r,g,b]` arrays. Keys missing from a page fall back to defaults, so older files keep rendering exactly as
before (e.g. files written before `paper`, `overprint`, `ink2` and `tape` existed). Rendering is deterministic for a
given `seed`, so the same file produces the same page in both versions. Readers ignore every other entry in the zip.
