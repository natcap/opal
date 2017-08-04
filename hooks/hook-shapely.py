from PyInstaller.compat import is_win
import os

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

import shapely
hiddenimports = collect_submodules('shapely')
datas = collect_data_files('shapely')

if is_win:
    datas += [(os.path.join(shapely.__path__[0], 'DLLs/geos_c.dll'), '')]
