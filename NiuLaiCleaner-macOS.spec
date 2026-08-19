# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/cow-walk.png', 'assets'),
        ('assets/cow-point.png', 'assets'),
        ('assets/cow-graze.png', 'assets'),
        ('assets/cow-run.png', 'assets'),
        ('assets/cow-aim-background-v1.png', 'assets'),
        ('assets/mama.wav', 'assets'),
        ('assets/shoot.wav', 'assets'),
        ('assets/hoof.wav', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NiuLaiCleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NiuLaiCleaner',
)
app = BUNDLE(
    coll,
    name='NiuLaiCleaner.app',
    icon=None,
    bundle_identifier='com.ai-training-camp.niulai-cleaner',
    info_plist={
        'CFBundleDisplayName': '牛来清理桌面',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'File to feed the cow',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['public.data', 'public.folder'],
            },
        ],
    },
)
