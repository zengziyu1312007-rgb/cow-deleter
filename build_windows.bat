@echo off
setlocal
cd /d "%~dp0"

if not exist .build-venv-windows\Scripts\python.exe (
  py -3.12 -m venv .build-venv-windows
)

.build-venv-windows\Scripts\python.exe -m pip install --upgrade pip
.build-venv-windows\Scripts\pip.exe install -r requirements.txt pyinstaller
.build-venv-windows\Scripts\pyinstaller.exe --noconfirm --clean NiuLaiCleaner.spec

echo Built: %CD%\dist\NiuLaiCleaner.exe
endlocal
