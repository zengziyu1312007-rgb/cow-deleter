# Cow Deleter (牛来清理桌面)

A playful desktop pet: a cow walks onto your screen, "eats" every file on the desktop (sends them to the Recycle Bin via `send2trash`, so it's recoverable), then walks off.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

## Build a standalone EXE

```bash
pip install pyinstaller
pyinstaller NiuLaiCleaner.spec
```

The built executable will be in `dist/`.

## Notes

- Files are moved to the Recycle Bin, not permanently deleted.
- Target directory defaults to the current user's Desktop; override with the `NIULAI_TARGET_DIR` environment variable.
