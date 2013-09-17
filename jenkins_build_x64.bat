SET ENVDIR=adept_environment
DEL /S /Q build
DEL /S /Q %ENVDIR%

IF "%1" == "" SET PYTHON=C:\py27_build\python.exe
IF NOT "%1" == "" SET PYTHON="%1"

%PYTHON% bootstrap_adept_environment.py > setup_environment.py
%PYTHON% setup_environment.py --clear --system-site-packages %ENVDIR%

cd invest-natcap.invest-3
echo %~dp0
echo "--- Compiling invest-3 ---"
..\%ENVDIR%\Scripts\python setup.py build_ext install
cd ..

echo "--- CD to Adept folder ---"

echo "--- Building Adept ---"
echo %~dp0
SET PATH=%PATH%;%ENVDIR%\Lib\site-packages
%ENVDIR%\Scripts\python setup.py py2exe win_installer bdist_wininst
echo "--- Finished building Adept ---"
