SET ENVDIR=adept_environment
DEL /S /Q build
DEL /S /Q %ENVDIR%

IF "%1" == "" SET PYTHON=C:\py27_build\python.exe
IF NOT "%1" == "" SET PYTHON="%1"

%PYTHON% bootstrap_adept_environment.py > setup_environment.py
%PYTHON% setup_environment.py --clear --system-site-packages %ENVDIR%
copy C:\Python27\Lib\distutils\distutils.cfg .\%ENVDIR%\Lib\distutils\distutils.cfg
cd invest-natcap.invest-3
..\%ENVDIR%\Scripts\python setup.py build_ext install
cd ..

%ENVDIR%\Scripts\python setup.py py2exe win_installer bdist_wininst
