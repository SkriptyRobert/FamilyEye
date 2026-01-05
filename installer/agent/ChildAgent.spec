# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Administrator\\Documents\\Cursor\\Parential-Control_Enterprise\\clients\\windows\\child_agent.py'],
    pathex=['C:\\Users\\Administrator\\Documents\\Cursor\\Parential-Control_Enterprise\\clients\\windows'],
    binaries=[],
    datas=[('C:\\Users\\Administrator\\Documents\\Cursor\\Parential-Control_Enterprise\\clients\\windows\\agent', 'agent')],
    hiddenimports=['psutil', 'win32pipe', 'win32file', 'pywintypes', 'winerror', 'agent', 'agent.ipc_common', 'agent.ipc_client', 'agent.ui_overlay'],
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
    a.binaries,
    a.datas,
    [],
    name='ChildAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
