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

common_kwargs = {
    'hookspath': ['./hooks'],
    'runtime_hooks': ['./hooks/rthook.py'],
    'hiddenimports': ['adept', 'adept.static_maps'],
}

opal_analysis = Analysis(['run_opal.py'], ** common_kwargs)
pyz = PYZ(opal_analysis.pure)

# produce one application per operation mode: a console application and a
# non-console application. The non-console application should be called from
# the start menu.
OPAL_EXES = []
for console in [True, False]:
    if console is True:
        console_str = '_debug'
    else:
        console_str = ''

    if platform.system() == 'Windows':
        exe_name = 'opal_exe%s.exe' % console_str
        debug_program = False
    else:
        exe_name = 'opal_exe%s' % console_str
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
              console=console)
    OPAL_EXES.append(opal_exe)

extra_data_files = ['carbon_sm.json', 'sediment_sm.json', 'nutrient_sm.json',
    'generic_sm.json', 'opal.json']

# dump the correct version information to the dist_version file.
dist_data = versioning.build_data()
dist_data['dist_name'] = 'OPAL'
dist_version_uri = 'build/dist_version.json'
json.dump(dist_data, open(dist_version_uri, 'w+'))

total_coll = COLLECT(
    [('dist_version.json', dist_version_uri, 'DATA')],
    [(json_name, json_name, 'DATA') for json_name in extra_data_files],
    opal_analysis.binaries,
    opal_analysis.zipfiles,
    opal_analysis.datas,
    *OPAL_EXES,
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
        # use the GUI version of the EXE.
        batfile = open(batfile_uri, 'w')
        batfile.write('opal_exe.exe %s\n' % json_filename)
        batfile.close()


