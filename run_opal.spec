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

from natcap.opal import versioning

common_kwargs = {
    'hookspath': ['./hooks'],
    'runtime_hooks': ['./hooks/rthook.py'],
    'hiddenimports': ['natcap.opal', 'natcap.opal.static_maps', 'os', 'traceback',
        'run_opal'],
}

# write the static map analysis objects and analyze them.
static_json_files = ['opal_carbon_sm.json', 'opal_generic_sm.json', 'opal_nutrient_sm.json',
    'opal.json', 'opal_sediment_sm.json']
analysis_objects = []

# analyze opal, append to the analysis objects
opal_analysis = Analysis(['run_opal.py'], **common_kwargs)
analysis_objects.append((opal_analysis, 'run_opal', 'run_opal'))

consoles = []
for json_file in static_json_files:
    json_base = json_file.replace('.json', '')
    console_filename = 'gui_%s.py' % json_base
    if os.path.exists(console_filename):
        raise Exception('File %s exists ... aborting' % console_filename)

    # Writing the GUI console file as a clone of run_opal python file.
    console_file = open(console_filename, 'w')
    run_opal_file = open('run_opal.py', 'r')
    for line in run_opal_file:
        if line.startswith('if __name__ '):
            continue  # totally skip the if__name__ == __main__ line
        if line.startswith('    main()'):
            line = "main('%s')\n" % json_file
        console_file.write(line)
    console_file.close()
    run_opal_file.close()

    console_analysis = Analysis([console_filename], **common_kwargs)
    analysis_objects.append((console_analysis, json_base, json_base))
    consoles.append((console_analysis, json_file))

# merge all of the builds together
MERGE(*analysis_objects)

pyz = PYZ(opal_analysis.pure)

# produce one application per operation mode: a console application and a
# non-console application. The non-console application should be called from
# the start menu.
OPAL_EXES = []
for console in [True]:  # only create a console application for core OPAL
    if console is True:
        console_str = '_cli'
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

for console_analysis, json_file in consoles:
    app_name = 'gui_%s' % json_file.replace('.json', '')
    if platform.system() == 'Windows':
        app_name += '.exe'

    pyz = PYZ(console_analysis.pure)
    exe = EXE(
        pyz,
        console_analysis.scripts,
        console_analysis.zipfiles,
        console_analysis.binaries,
        name=app_name,
        debug=False,
        onefile=False,
        exclude_binaries=True,  # make all files located in same dir
        strip=False,
        upx=False,
        console=False  # Force a GUI application
    )
    OPAL_EXES.append(exe)
    OPAL_EXES.append(console_analysis.binaries)
    OPAL_EXES.append(console_analysis.zipfiles)
    OPAL_EXES.append(console_analysis.datas)

# dump the correct version information to the dist_version file.
dist_data = versioning.build_data()
dist_data['dist_name'] = 'OPAL'
dist_version_uri = 'build/dist_version.json'
json.dump(dist_data, open(dist_version_uri, 'w+'))

total_coll = COLLECT(
    [('dist_version.json', dist_version_uri, 'DATA')],
    [(json_name, json_name, 'DATA') for json_name in static_json_files],
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
    if not os.path.exists(source_file):
        # Shapely moved their DLL location recently.
        source_file = os.path.join(pkg_dir, 'DLLs', 'geos_c.dll')

    dest_file = os.path.join('dist', 'total_coll', 'geos_c.dll')
    shutil.copyfile(source_file, dest_file)

    # write the bat files to launch the proper ui.
    for json_filename in static_json_files:
        batfile_name = 'run_%s.bat' % os.path.splitext(json_filename)[0].replace('opal_', '')
        batfile_uri = os.path.join(os.getcwd(), 'dist', 'total_coll', batfile_name)

        # write the contents of the launch batfile.
        # use the CLI ('debug') version of the EXE.
        batfile = open(batfile_uri, 'w')
        batfile.write('opal_exe_cli.exe %s\n' % json_filename)
        batfile.close()


