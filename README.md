# Cow Deleter (牛来清理桌面)

A playful transparent desktop overlay. The real Finder/Desktop stays visible while you aim at the selected file, confirm the cow's question, and watch the file turn into grass before the cow eats it. The file is sent to the Recycle Bin via `send2trash`, so it is recoverable.

The interaction follows the original MonsterDeleter rhythm: target a file with the red crosshair, wait for the cow to walk over and point at it, confirm the cow's question, watch the file transform into grass, then hear the hoofbeats as the cow leaves.

On Windows, launching the app once registers the file context-menu action `召唤牛来吃掉`. On macOS, a file can be dragged onto the app; launching without a file opens the in-app fallback selector.

## 一句话安装（macOS）

把这个仓库交给 Codex、Cursor 或 Claude Code，然后直接说：

> **帮我安装牛来清理文件**

AI 会按仓库里的 `AGENTS.md` 自动完成构建、Finder 右键快速操作安装和结果验证。也可以手动执行同一个入口：

```bash
./install.sh
```

首次安装需要联网下载依赖，并需要 Python 3.10 或更高版本。安装完成后，在 Finder 里选中文件：**右键 → 快速操作 → 牛来清理文件**。

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

## Build the Windows app

```bash
build_windows.bat
```

Run this on Windows with Python 3.12 installed. The executable is written to `dist/NiuLaiCleaner.exe`.

## Build the macOS app

```bash
./build_macos.sh
```

The application bundle is written to `dist/NiuLaiCleaner.app`.

### Install the Finder right-click action

```bash
./install_macos_quick_action.sh
```

This copies the app to `~/Applications/NiuLaiCleaner.app` and installs the Finder service `牛来清理文件`. In Finder, right-click a file and choose **Quick Actions → 牛来清理文件** (or **Services → 牛来清理文件**, depending on the macOS menu layout).

## Notes

- Files are moved to the Recycle Bin, not permanently deleted.
- Target directory defaults to the current user's Desktop; override with the `NIULAI_TARGET_DIR` environment variable.
- For a safe demo, always set `NIULAI_TARGET_DIR` to a folder containing disposable sample files.
