from PyInstaller.hooks.hookutils import collect_data_files

hiddenimports = ['faulthandler']
datas = collect_data_files('adept')
