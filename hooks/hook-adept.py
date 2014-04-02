import os
import adept

#from hookutils import collect_submodules
#hiddenimports = collect_submodules('adept')
hiddenimports = ['adept', 'invest_natcap', 'palisades']

adept_dir = os.path.dirname(adept.__file__)
datas = [
    (os.path.join(adept_dir, 'report_data', '*'), 'report_data')
]
