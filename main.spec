# -*- mode: python ; coding: utf-8 -*-

import importlib.util
import os

def getPackagePath(package_name):
    spec = importlib.util.find_spec(package_name)
    if spec and spec.origin:
        package_dir = os.path.dirname(spec.origin)
        return package_dir
    else:
        raise ImportError(f"未找到包 {package_name}")

package_path = getPackagePath("AoE2ScenarioParser")

added_files = [
         ( f'{package_path}/versions/DE/v1.56/conditions.json', './AoE2ScenarioParser/versions/DE/v1.56'), 
         ( f'{package_path}/versions/DE/v1.56/effects.json', './AoE2ScenarioParser/versions/DE/v1.56'), 
         ( f'{package_path}/versions/DE/v1.56/structure.json', './AoE2ScenarioParser/versions/DE/v1.56'), 
         ( f'{package_path}/versions/DE/v1.56/default.aoe2scenario', './AoE2ScenarioParser/versions/DE/v1.56'), 
         ]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
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
    a.binaries,
    a.datas,
    [],
    name='Trigger Craft',
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
    icon=['AoE2TC.ico'],
    version='_prebuild/version.txt',
)
