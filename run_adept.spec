# -*- mode: python -*-

# ALSO:
#  * tweak shapely.geos to work on a mac via pyinstaller .. currently not supported.
#  * Copy the matplotlib data folder mpl_data to the execution folder (in dist)

import matplotlib
print matplotlib._get_data_path()

import sys
for item in sys.path:
    print item
a = Analysis(['run_adept.py'],
             pathex=['/Users/jdouglass/workspace/invest-natcap.permitting',
                     '/Users/jdouglass/workspace/invest-natcap.permitting/adept_py_env/lib/',
                     '/Users/jdouglass/workspace/invest-natcap.permitting/adept_py_env/lib/site-packages'],
             hookspath=['./hooks'],
             runtime_hooks=['hooks/hook-adept.py', 'hooks/hook-adept.adept_core.py'])


a.datas += [('adept.json', 'adept.json', 'DATA')]

mpl_data_tree = Tree(matplotlib._get_data_path(), prefix='mpl-data')
adept_pkg_static = Tree('adept/adept/static_data', prefix='static_data')

pyz = PYZ(a.pure)

import platform
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          name='run_adept_%s' % platform.platform(),
          debug=False,
          strip=None,
          upx=False,  # says UPX is not available
          append_pkg=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               mpl_data_tree,
               adept_pkg_static,
               strip=None,
               upx=True,
               name='run_adept_coll_%s' % platform.platform())
app = BUNDLE(coll,
             name='run_adept.app',
             icon=None)
