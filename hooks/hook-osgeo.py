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
        pkg_base, pkg_dir = get_package_paths('Shapely')
    except ImportError:
        pkg_base, pkg_dir = get_package_paths('osgeo')
    datas = [(os.path.join(pkg_dir, filename), '') for filename in files]
