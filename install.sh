#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "$(uname -s)" != "Darwin" ]; then
    echo "牛来清理文件的一键安装目前仅支持 macOS。" >&2
    echo "Windows 请在本项目目录运行 build_windows.bat。" >&2
    exit 1
fi

if [ -n "${PYTHON_BIN:-}" ]; then
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        echo "找不到指定的 Python：$PYTHON_BIN" >&2
        exit 1
    fi
else
    for candidate in python3.12 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && \
            "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
            PYTHON_BIN=$candidate
            break
        fi
    done
fi

if [ -z "${PYTHON_BIN:-}" ]; then
    echo "没有找到 Python 3.10 或更高版本。请先安装 Python，再重新执行本脚本。" >&2
    exit 1
fi

echo "🐮 正在构建牛来清理文件（首次运行会下载依赖）……"
PYTHON_BIN="$PYTHON_BIN" "$SCRIPT_DIR/build_macos.sh"

echo "🐮 正在安装应用和 Finder 快速操作……"
"$SCRIPT_DIR/install_macos_quick_action.sh"

APP_TARGET="$HOME/Applications/NiuLaiCleaner.app"
SERVICE_TARGET="$HOME/Library/Services/牛来清理文件.workflow"
test -d "$APP_TARGET"
test -d "$SERVICE_TARGET"

echo ""
echo "✅ 安装完成"
echo "使用方法：Finder 选中文件 → 右键 → 快速操作 → 牛来清理文件"
echo "如果菜单暂未出现，请重新打开 Finder 后再试。"
