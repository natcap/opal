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

opal_analysis = Analysis(['run_opal.py'], ** common_kwargs)
pyz = PYZ(opal_analysis.pure)

if platform.system() == 'Windows':
    exe_name = 'opal_exe.exe'
    debug_program = False
else:
    exe_name = 'opal_exe'
    debug_program = True

opal_exe = EXE(pyz,
          opal_analysis.scripts,
          opal_analysis.dependencies,
          name=exe_name,
          debug=debug_program,
          exclude_binaries=True,  # makes all files located in same dir
          strip=None,
          upx=False,  # says UPX is not available
          append_pkg=True,
          console=CONSOLE)

extra_data_files = ['carbon_sm.json', 'sediment_sm.json', 'nutrient_sm.json',
    'generic_sm.json', 'opal.json']

exe_objects = []
analysis_items = [adept_exe]

# dump the correct version information to the dist_version file.
dist_data = versioning.build_data()
dist_data['dist_name'] = 'OPAL'
dist_version_uri = 'build/dist_version.json'
json.dump(dist_data, open(dist_version_uri, 'w+'))

total_coll = COLLECT(
    [('dist_version.json', dist_version_uri, 'DATA')],
    [(json_name, json_name, 'DATA') for (_, json_name) in json_files],
    opal_analysis.binaries,
    opal_analysis.zipfiles,
    opal_analysis.datas,
    *analysis_items,
    strip=None,
    upx=False,
    exclude_binaries=True,
    name='total_coll'
)

# FORCE the usage of the shapely version of geos_c.dll and write the opal
# .bat scripts
if is_win:
    pkg_base, pkg_dir = get_package_paths('shapely')
    source_file = os.path.join(pkg_dir, 'geos_c.dll')
    dest_file = os.path.join('dist', 'total_coll', 'geos_c.dll')
    shutil.copyfile(source_file, dest_file)

    # write the bat files to launch the proper ui.
    for json_filename in extra_data_files:
        batfile_name = 'run_%s.bat' % os.path.splitext(json_filename)[0]
        batfile_uri = os.path.join(os.getcwd(), 'dist', 'total_coll', batfile_name)

        # write the contents of the launch batfile.
        batfile = open(batfile_name, 'w')
        batfile.write('opal_exe.exe %s\n' % json_filename)
        batfile.close()


