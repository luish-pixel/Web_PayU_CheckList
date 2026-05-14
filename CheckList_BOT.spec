# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [('static', 'static'), ('fonts', 'fonts'), ('Prompts_AI', 'Prompts_AI'), ('ms-playwright', 'ms-playwright'), ('MCC_Info.xlsx', '.')]
datas += copy_metadata('werkzeug')
datas += copy_metadata('flask')


a = Analysis(
    ['app_flask_case.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['flask', 'jinja2', 'werkzeug', 'asyncio', 'reportlab', 'reportlab.pdfgen', 'reportlab.platypus', 'playwright', 'playwright.async_api', 'pandas', 'openpyxl', 'sqlite3', 'PIL', 'PIL.Image', 'requests', 'tkinter'],
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
    name='CheckList_BOT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CheckList_BOT',
)
