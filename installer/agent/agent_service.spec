# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Administrator\\Documents\\Cursor\\Parential-Control_Enterprise\\installer\\agent\\agent_service_src.py'],
    pathex=['C:\\Users\\Administrator\\Documents\\Cursor\\Parential-Control_Enterprise\\clients\\windows'],
    binaries=[],
    datas=[('C:\\Users\\Administrator\\Documents\\Cursor\\Parential-Control_Enterprise\\clients\\windows\\agent', 'agent')],
    hiddenimports=['win32timezone', 'win32serviceutil', 'win32service', 'win32event', 'servicemanager', 'psutil', 'requests', 'urllib3', 'colorama', 'websockets', 'win32gui', 'win32process', 'win32con', 'win32api', 'win32security', 'win32ts', 'win32pipe', 'win32file', 'pywintypes', 'winerror', 'ntsecuritycon', 'agent', 'agent.main', 'agent.ipc_common', 'agent.ipc_server', 'agent.ipc_client', 'agent.ui_overlay', 'agent.notifications', 'agent.logger', 'agent.config'],
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
    name='agent_service',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
