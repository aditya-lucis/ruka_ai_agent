# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['src.config', 'src.llm.gemini_client', 'src.ruka_cognition.brain', 'src.ruka_cognition.neural.features', 'src.ruka_cognition.context.relevance', 'src.tools.google_search', 'ruka_companion.voice.tts', 'ruka_companion.voice.asr', 'ruka_companion.identity.engine', 'ruka_companion.identity.types', 'ruka_companion.vision.camera', 'ruka_companion.presence.engine', 'ruka_persistence.store', 'sqlite3', 'pydantic', 'numpy']
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('google.genai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('lxml')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('certifi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pywhispercpp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


import os
from pathlib import Path

BASE_DIR = Path(SPECPATH).resolve() if "SPECPATH" in locals() else Path(".").resolve()

a = Analysis(
    [str(BASE_DIR / 'launcher.py')],
    pathex=[
        str(BASE_DIR / 'ruka-agent'),
        str(BASE_DIR / 'ruka-companion' / 'src'),
        str(BASE_DIR / 'ruka-persistence' / 'src'),
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='ruka-brain',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ruka-brain',
)
