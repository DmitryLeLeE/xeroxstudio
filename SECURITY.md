# Security and privacy

- The browser version processes photos entirely on your device. There is no server component, no analytics and no
  trackers; autosave is stored only in your browser (IndexedDB / localStorage).
- The Windows app works offline and writes only to `%LOCALAPPDATA%\XeroxZineStudio\` and the files you choose.
- `.zine` files are zip archives ([format](docs/zine-format.md)): both versions read only `manifest.json` and `images/*.png` and ignore everything else.

To report a vulnerability, open a private security advisory on the repository
(Security → Report a vulnerability) rather than a public issue.
