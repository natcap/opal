# -*- mode: python -*-

# ALSO:
#  * tweak shapely.geos to work on a mac via pyinstaller .. currently not supported.
#  * Copy the matplotlib data folder mpl_data to the execution folder (in dist)

import matplotlib
print matplotlib._get_data_path()

import sys
for item in sys.path:
    print item
a = Analysis(['run_adept.py', 'run_carbon_sm.py', 'run_sediment_sm.py', 'run_nutrient_sm.py'], hookspath=['./hooks'],
    runtime_hooks=['./hooks/rthook.py'])

pyz = PYZ(a.pure)

import platform
if platform.system() == 'Windows':
    exe_name = 'run_adept.exe'
else:
    exe_name = 'run_adept'
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.datas,
          name=exe_name,
          debug=True,
          strip=None,
          upx=False,  # says UPX is not available
          append_pkg=True,
          console=False)
coll = COLLECT(exe,
               [('adept.json', 'adept.json', 'DATA')],
               strip=None,
               upx=False,
               name='run_adept_coll')  # the output folder name.
app = BUNDLE(coll,
             name='run_adept.app',
             icon=None)
