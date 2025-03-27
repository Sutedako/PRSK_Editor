# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['src/Main.pyw', 'src/ListManager.py', 'src/Editor.py', 'src/JsonLoader.py', 'src/mainGUI.py', 'src/Dictionary.py'],
             pathex=['/Users/linyuan/Desktop/PRSK_Editor'],
             binaries=[],
             datas=[('image', 'image')],
             hiddenimports=[],
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
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='Sekai Text',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='image/icon/256.icns',
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
app = BUNDLE(exe,
             name='Sekai Text.app',
             icon='image/icon/256.icns',
             bundle_identifier=None)