from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('palisades')
hiddenimports = collect_submodules('palisades')
