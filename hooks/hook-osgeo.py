from PyInstaller.compat import is_win
from PyInstaller.hooks.hookutils import get_package_paths
import os

if is_win:
    files = [
        'geos_c.dll',
    ]
    # If shapely is present, use that version of GEOS_C.dll
    try:
        import shapely
        pkg_dir = os.path.dirname(shapely.__file__)
    except (ImportError, AssertionError) as error:
        # ImportError is raised when we can't import shapely
        # AssertionError is raised when the package path can't be found.
        print 'Defaulting to osgeo pkg:', error
        pkg_base, pkg_dir = get_package_paths('osgeo')
    datas = [(os.path.join(pkg_dir, filename), '') for filename in files]

    data_dir = os.path.join(pkg_dir, 'data', 'gdal')
    datas += [(os.path.join(data_dir, filename), '') for filename in
            os.listdir(data_dir)]
