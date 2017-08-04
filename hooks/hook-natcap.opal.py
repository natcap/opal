from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('natcap.opal')
hiddenimports = collect_submodules('natcap.opal')
