# -*- mode: python -*-

# ALSO:
#  * tweak shapely.geos to work on a mac via pyinstaller .. currently not supported.
#  * Copy the matplotlib data folder mpl_data to the execution folder (in dist)

import matplotlib
print matplotlib._get_data_path()
import platform

import sys
for item in sys.path:
    print item

#a = Analysis(['run_adept.py', 'run_carbon_sm.py', 'run_sediment_sm.py', 'run_nutrient_sm.py'], hookspath=['./hooks'],
#    runtime_hooks=['./hooks/rthook.py'])

common_kwargs = {
    'hookspath': ['./hooks'],
    'runtime_hooks': ['./hooks/rthook.py'],
    'hiddenimports': ['adept'],
}

adept_analysis = Analysis(['run_adept.py'], **common_kwargs)
carbon_analysis = Analysis(['run_carbon_sm.py'], **common_kwargs)
sediment_analysis = Analysis(['run_nutrient_sm.py'], **common_kwargs)
nutrient_analysis = Analysis(['run_sediment_sm.py'], **common_kwargs)

# Merge all of the analysis objects together.
MERGE(
    (adept_analysis, 'run_adept', 'adept'),
    (carbon_analysis, 'run_carbon_sm', 'carbon_sm'),
    (sediment_analysis, 'run_sediment_sm', 'sediment_sm'),
    (nutrient_analysis, 'run_nutrient_sm', 'nutrient_sm'),
)

pyz = PYZ(adept_analysis.pure)

#import platform
if platform.system() == 'Windows':
    exe_name = 'run_adept.exe'
    debug_program = False
else:
    exe_name = 'run_adept'
    debug_program = True
adept_exe = EXE(pyz,
          adept_analysis.scripts,
#          adept_analysis.binaries,
#          adept_analysis.zipfiles,
          adept_analysis.dependencies,
#          adept_analysis.datas,
          name='adept_exe',
          debug=debug_program,
          exclude_binaries=True,  # makes all files located in same dir
          strip=None,
          upx=False,  # says UPX is not available
          append_pkg=True,
          console=False)
#adept_coll = COLLECT(adept_exe,
#               [(name, name, 'DATA') for name in ['adept.json', 'carbon_sm.json', 'sediment_sm.json', 'nutrient_sm.json']],
#               strip=None,
#               upx=False,
#               name='run_adept_coll')  # the output folder name.
#app = BUNDLE(adept_coll,
#             name='run_adept.app',
#             icon=None)


exe_files = [
#    (adept_analysis, 'adept.json'),
    (carbon_analysis, 'carbon_sm.json'),
    (sediment_analysis, 'sediment_sm.json'),
    (nutrient_analysis, 'nutrient_sm.json'),
]

exe_objects = []

for analysis, json_file in exe_files:
    name = json_file.replace('.json', '')
    if platform.system() == 'Windows':
        name += '.exe'
    print name

    pyz = PYZ(analysis.pure)

#    for d in analysis.datas:
#        if 'Makefile' in d[0]:
#            analysis.datas.remove(d)
#            break

    print name, 'exe'
    exe = EXE(
        pyz,
        analysis.scripts,
        #        analysis.dependencies,
#        analysis.zipfiles,
#        analysis.binaries,
#        analysis.datas,
        name=name,
        debug=True,
        onefile=False,
#        strip=None,
        exclude_binaries=True,  # makes all files located in same dir
        strip=False,
        upx=False,
    )
    print name, 'coll'
    #exe_objects.append(exe)
    coll = COLLECT(
        exe,
        [(json_file, json_file, 'DATA')],
        analysis.binaries,
        analysis.zipfiles,
        analysis.datas,
        strip=None,
        upx=False,  # must be False on mac
        name=name
    )

total_coll = COLLECT(
    adept_exe,
#    [(json_file, json_file, 'DATA') for (a, json_file) in exe_files],
    [('adept.json', 'adept.json', 'DATA')],
#    *exe_objects,
    adept_analysis.binaries,
    adept_analysis.zipfiles,
    adept_analysis.datas,
    strip=None,
#    upx=False,
    name='total_coll'
)
