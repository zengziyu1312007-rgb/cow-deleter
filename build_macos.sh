#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python3.12}
BUILD_ENV=.build-venv-macos

"$PYTHON_BIN" -m venv "$BUILD_ENV"
"$BUILD_ENV/bin/python" -m pip install --upgrade pip
"$BUILD_ENV/bin/pip" install -r requirements.txt pyinstaller
"$BUILD_ENV/bin/pyinstaller" --noconfirm --clean NiuLaiCleaner-macOS.spec

echo "Built: $SCRIPT_DIR/dist/NiuLaiCleaner.app"
