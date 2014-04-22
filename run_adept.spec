# -*- mode: python -*-

# ALSO:
#  * tweak shapely.geos to work on a mac via pyinstaller .. currently not supported.
#  * Copy the matplotlib data folder mpl_data to the execution folder (in dist)

import matplotlib
print matplotlib._get_data_path()
import platform

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

if platform.system() == 'Windows':
    exe_name = 'run_adept.exe'
    debug_program = False
else:
    exe_name = 'run_adept'
    debug_program = True
adept_exe = EXE(pyz,
          adept_analysis.scripts,
          adept_analysis.dependencies,
          name='adept_exe',
          debug=debug_program,
          exclude_binaries=True,  # makes all files located in same dir
          strip=None,
          upx=False,  # says UPX is not available
          append_pkg=True,
          console=False)

exe_files = [
    (carbon_analysis, 'carbon_sm.json'),
    (sediment_analysis, 'sediment_sm.json'),
    (nutrient_analysis, 'nutrient_sm.json'),
]

exe_objects = []
analysis_items = [adept_exe]

for analysis, json_file in exe_files:
    name = json_file.replace('.json', '')
    if platform.system() == 'Windows':
        name += '.exe'
    print name

    pyz = PYZ(analysis.pure)

    print name, 'exe'
    exe = EXE(
        pyz,
        analysis.scripts,
#        analysis.dependencies,  # causes crash when Mach-O reads .nib file
        analysis.zipfiles,
        analysis.binaries,
#        analysis.datas,
        name=name,
        debug=True,
        onefile=False,
#        strip=None,
        exclude_binaries=True,  # makes all files located in same dir
        strip=False,
        upx=False,
    )
    analysis_items.append(exe)
    for item in [analysis.binaries, analysis.zipfiles, analysis.datas]:
        analysis_items.append(item)

total_coll = COLLECT(
    [('adept.json', 'adept.json', 'DATA')],
    adept_analysis.binaries,
    adept_analysis.zipfiles,
    adept_analysis.datas,
    *analysis_items,
    strip=None,
    upx=False,
    exclude_binaries=True,
    name='total_coll'
)
