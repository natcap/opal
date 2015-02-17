# -*- mode: python -*-

# ALSO:
#  * tweak shapely.geos to work on a mac via pyinstaller .. currently not supported.
#  * Copy the matplotlib data folder mpl_data to the execution folder (in dist)


from PyInstaller.compat import is_win
from PyInstaller.hooks.hookutils import get_package_paths
import os
import matplotlib
print matplotlib._get_data_path()
import platform
import json
import shutil

from adept import versioning

CONSOLE = True

common_kwargs = {
    'hookspath': ['./hooks'],
    'runtime_hooks': ['./hooks/rthook.py'],
    'hiddenimports': ['adept', 'adept.static_maps'],
}

adept_analysis = Analysis(['run_adept.py'], **common_kwargs)
carbon_analysis = Analysis(['run_carbon_sm.py'], **common_kwargs)
sediment_analysis = Analysis(['run_sediment_sm.py'], **common_kwargs)
nutrient_analysis = Analysis(['run_nutrient_sm.py'], **common_kwargs)
custom_analysis = Analysis(['run_custom_sm.py'], **common_kwargs)

# Merge all of the analysis objects together.
MERGE(
    (adept_analysis, 'run_adept', 'opal'),
    (carbon_analysis, 'run_carbon_sm', 'carbon_sm'),
    (sediment_analysis, 'run_sediment_sm', 'sediment_sm'),
    (nutrient_analysis, 'run_nutrient_sm', 'nutrient_sm'),
    (custom_analysis, 'run_custom_sm', 'custom_sm'),
)

pyz = PYZ(adept_analysis.pure)

if platform.system() == 'Windows':
    exe_name = 'opal_exe.exe'
    debug_program = False
else:
    exe_name = 'opal_exe'
    debug_program = True

adept_exe = EXE(pyz,
          adept_analysis.scripts,
          adept_analysis.dependencies,
          name=exe_name,
          debug=debug_program,
          exclude_binaries=True,  # makes all files located in same dir
          strip=None,
          upx=False,  # says UPX is not available
          append_pkg=True,
          console=CONSOLE)

exe_files = [
    (carbon_analysis, 'carbon_sm.json'),
    (sediment_analysis, 'sediment_sm.json'),
    (nutrient_analysis, 'nutrient_sm.json'),
    (custom_analysis, 'generic_sm.json'),
]

exe_objects = []
analysis_items = [adept_exe]

for analysis, json_file in exe_files:
    name = json_file.replace('.json', '')
    if platform.system() == 'Windows':
        name += '.exe'

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
        debug=False,
        onefile=False,
#        strip=None,
        exclude_binaries=True,  # makes all files located in same dir
        strip=False,
        upx=False,
        console=CONSOLE
    )
    analysis_items.append(exe)
    for item in [analysis.binaries, analysis.zipfiles, analysis.datas]:
        analysis_items.append(item)

# dump the correct version information to the dist_version file.
dist_data = versioning.build_data()
dist_data['dist_name'] = 'OPAL'
dist_version_uri = 'build/dist_version.json'
json.dump(dist_data, open(dist_version_uri, 'w+'))

total_coll = COLLECT(
    [('adept.json', 'adept.json', 'DATA')],
    [('dist_version.json', dist_version_uri, 'DATA')],
    [(json_name, json_name, 'DATA') for (_, json_name) in exe_files],
    adept_analysis.binaries,
    adept_analysis.zipfiles,
    adept_analysis.datas,
    *analysis_items,
    strip=None,
    upx=False,
    exclude_binaries=True,
    name='total_coll_mafe'
)

# FORCE the usage of the shapely version of geos_c.dll.
if is_win:
    pkg_base, pkg_dir = get_package_paths('shapely')
    source_file = os.path.join(pkg_dir, 'geos_c.dll')
    if not os.path.exists(source_file):
        source_file = os.path.join(pkg_dir, 'DLLs', 'geos_c.dll')

    dest_file = os.path.join('dist', 'total_coll_mafe', 'geos_c.dll')
    shutil.copyfile(source_file, dest_file)
