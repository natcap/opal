import glob
import os

import invest_natcap

from PyInstaller.hooks.hookutils import get_package_paths

hidden_imports = ['scipy.special._ufuncs_cxx']

#pkg_base, pkg_dir = get_package_paths('invest_natcap')
invest_dir = os.path.dirname(invest_natcap.__file__)
datas = [
    (os.path.join(invest_dir, 'reporting', 'reporting_data', '*.js'),
        'reporting_data'),
]
