# -*- mode: python ; coding: utf-8 -*-
import sys

a = Analysis(
    ['packaging/entry.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    # One-dir + .app bundle (onefile clashes with macOS security; deprecated).
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='DeskBridge',
        debug=False,
        strip=False,
        upx=False,
        console=False,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name='DeskBridge',
    )
    app = BUNDLE(
        coll,
        name='DeskBridge.app',
        icon=None,
        bundle_identifier='org.deskbridge.app',
    )
else:
    # One-file executable (single DeskBridge.exe on Windows).
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='DeskBridge',
        debug=False,
        strip=False,
        upx=False,
        console=False,
    )
