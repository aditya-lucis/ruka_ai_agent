# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'src.config',
    'src.llm.gemini_client',
    'src.ruka_cognition.brain',
    'src.ruka_cognition.agentic',
    'src.gateway.confirmations',
    'src.ruka_cognition.neural.features',
    'src.ruka_cognition.context.relevance',
    'src.tools.base',
    'src.tools.registry',
    'src.tools.builtin',
    'src.tools.coding',
    'src.tools.git',
    'src.tools.project_map',
    'src.tools.google_search',
    'src.tools.ambient_sensors',
    'src.agent.evaluator',
    'src.agent.self_correction',
    'src.agent.test_fix_verify',
    'src.agent.project_memory',
    'src.agent.plan_transparency',
    'src.neural.intent',
    'src.retrieval.store',
    'src.retrieval.reranker',
    'src.math_foundations.linear',
    'src.math_foundations.probability',
    'src.math_foundations.optimization',
    'src.math_foundations.information',
    'src.math_foundations.graph',
    'src.math_foundations.control',
    'src.math_foundations.statistical',
    'src.math_foundations.types',
    'src.gateway.server',
    'src.gateway.session',
    'src.gateway.events',
    'src.gateway.permissions',
    'src.gateway.protocol',
    'src.gateway.channels.base',
    'src.gateway.channels.desktop',
    'src.gateway.channels.cli',
    'src.gateway.supervisor',
    'src.memory.palace',
    'src.memory.palace.models',
    'src.memory.palace.vector',
    'src.memory.palace.palace',
    'src.memory.palace.consolidator',
    'src.senses',
    'src.senses.ear',
    'src.senses.voice',
    'src.senses.eyes',
    'src.hands',
    'src.heart',
    'src.heart.heart_eval',
    'src.converse',
    'src.converse.converse_eval',
    'src.presence',
    'src.os_companion',
    'src.os_companion.os_eval',
    'src.forge',
    'src.forge.forge_eval',
    'src.noctis_final_eval',
    'src.avatar',
    'src.gateway.skills.models',
    'src.gateway.skills.loader',
    'src.gateway.skills.registry',
    'src.gateway.skills.runtime',
    'src.gateway.skills.coding_bridge',
    'ruka_companion.voice.tts',
    'ruka_companion.voice.asr',
    'ruka_companion.identity.engine',
    'ruka_companion.identity.types',
    'ruka_companion.vision.camera',
    'ruka_companion.presence.engine',
    'ruka_persistence.store',
    'sqlite3',
    'pydantic',
    'numpy'
]
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
skills_folder = BASE_DIR / 'skills'
if skills_folder.exists():
    datas.append((str(skills_folder), 'skills'))

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
