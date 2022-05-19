# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

a = Analysis(['run_workbench.py'],
             pathex=[
             './venv/lib/python3.9/site-packages'
             ],
             binaries=[],
             datas=[
                ('pre_workbench/icons/*', 'pre_workbench/icons'),
                ('pre_workbench/structinfo/*.lark', 'pre_workbench/structinfo'),
                ('pre_workbench/*.tes', 'pre_workbench'),
                ('venv/lib/python3.9/site-packages/lark/grammars/common.lark', 'lark/grammars'),
             ],
             hiddenimports=[
                'PyQt5.QtPrintSupport',  # why ???
                'PyQtAds.ads'
             ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='PRE Workbench',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='PRE Workbench')
app = BUNDLE(coll,
             name='PRE Workbench.app',
             icon='appicon.icns',
             bundle_identifier=None)
