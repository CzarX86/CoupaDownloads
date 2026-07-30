# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/juliocezar/Dev/CoupaPilot/CoupaTurboDownloader/src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/juliocezar/Dev/CoupaPilot/CoupaTurboDownloader/src/gui/web', 'gui/web'), ('/Users/juliocezar/Dev/CoupaPilot/CoupaTurboDownloader/.version', '.')],
    hiddenimports=['extract_msg', 'fpdf', 'bs4', 'lxml', 'pandas', 'openpyxl', 'httpx', 'webview', 'selenium', 'selenium.webdriver.edge', 'selenium.webdriver.edge.webdriver', 'asyncio', 'json', 'sqlite3', 'process_all_pos'],
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
    name='ContractDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/juliocezar/Dev/CoupaPilot/CoupaTurboDownloader/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ContractDownloader',
)
app = BUNDLE(
    coll,
    name='ContractDownloader.app',
    icon='/Users/juliocezar/Dev/CoupaPilot/CoupaTurboDownloader/icon.icns',
    bundle_identifier='com.coupapilot.turbodownloader',
)
