# -*- mode: python -*-
a = Analysis(['run_adept.py'],
             pathex=['Z:\\workspace\\invest-natcap.permitting'],
             hiddenimports=['adept'],
             hookspath='.',
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='run_adept.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='run_adept')
