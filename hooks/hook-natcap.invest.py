from PyInstaller.hooks.hookutils import collect_data_files, collect_submodules
datas = collect_data_files('natcap.invest')
hiddenimports = collect_submodules('natcap.invest')
