SET ENVDIR=adept_environment
DEL /S /Q build
DEL /S /Q %ENVDIR%

IF "%1" == "" SET PYTHON=C:\py27_build\python.exe
IF NOT "%1" == "" SET PYTHON="%1"

%PYTHON% bootstrap_adept_environment.py > setup_environment.py
%PYTHON% setup_environment.py --clear --system-site-packages %ENVDIR%
copy C:\Python27\Lib\distutils\distutils.cfg .\%ENVDIR%\Lib\distutils\distutils.cfg

%ENVDIR%\Scripts\pip install windows_build\dbfpy-2.2.5.tar.gz

:: CD to the invest-3 directory to install it to the virtual environment
cd invest-natcap.invest-3
rmdir /S /Q build
..\%ENVDIR%\Scripts\python setup.py build_ext install || goto :error
cd ..
::
:: CD to the palisades directory to install it to the virtual environment
cd user-interface
rmdir /S /Q build
..\%ENVDIR%\Scripts\python setup.py build_ext install || goto :error
cd ..

:: CD to the Adept directory to install adept to the virtual environment
cd src/adept
rmdir /S /Q build
..\..\%ENVDIR%\Scripts\python setup.py install || goto :error
cd ..\..

:: Now that everything is installed, we can run the permitting project's
:: setup.py commands to build everything we want/need.
%ENVDIR%\Scripts\python src\pyinstaller\pyinstaller.py -y --onedir --noupx -c run_adept.spec || goto :error
%ENVDIR%\Scripts\python setup.py dist_colombia --nsis-dir=dist/total_coll || goto :error

goto :EOF

:error
exit /b %errorlevel%
