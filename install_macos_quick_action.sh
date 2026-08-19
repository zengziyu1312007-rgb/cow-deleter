#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_SOURCE="$SCRIPT_DIR/dist/NiuLaiCleaner.app"
APP_TARGET="$HOME/Applications/NiuLaiCleaner.app"
SERVICE_SOURCE="$SCRIPT_DIR/macos/牛来清理文件.workflow"
SERVICE_TARGET="$HOME/Library/Services/牛来清理文件.workflow"

mkdir -p "$HOME/Applications" "$HOME/Library/Services"
STAMP=$(date +%Y%m%d-%H%M%S)
if [ -e "$APP_TARGET" ]; then
    mv "$APP_TARGET" "$HOME/.Trash/NiuLaiCleaner-old-$STAMP.app"
fi
if [ -e "$SERVICE_TARGET" ]; then
    mv "$SERVICE_TARGET" "$HOME/.Trash/牛来清理文件-old-$STAMP.workflow"
fi
/usr/bin/ditto "$APP_SOURCE" "$APP_TARGET"
/usr/bin/ditto "$SERVICE_SOURCE" "$SERVICE_TARGET"
/System/Library/CoreServices/pbs -flush

echo "Installed app: $APP_TARGET"
echo "Installed Finder Quick Action: $SERVICE_TARGET"
