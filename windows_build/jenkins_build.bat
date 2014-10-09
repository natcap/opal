SET ENVDIR=adept_environment
DEL /S /Q build
DEL /S /Q %ENVDIR%

:: Set the default python if a python exe is not passed in as arg1
IF "%1" == "" SET PYTHON=C:\py27_build\python.exe
IF NOT "%1" == "" SET PYTHON="%1"

:: Indicate (via arg2) whether the build should include static data zips
IF "%2" == "" SET BUILD_STATIC_DATA="true"
IF NOT "%2" == "" SET BUILD_STATIC_DATA="%2"

:: Indicate via arg3 whether to build MAFE installer
IF "%3" == "" SET BUILD_MAFE="true"
IF NOT "%3" == "" SET BUILD_MAFE="%3"

:: Indicate via arg4 whether to build OPAL installer
IF "%4" == "" SET BUILD_OPAL="true"
IF NOT "%4" == "" SET BUILD_OPAL="%4"

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
cd src/palisades
rmdir /S /Q build
..\..\%ENVDIR%\Scripts\python setup.py build_ext install || goto :error
cd ..\..

:: CD to the faulthandler directory to install it to the virtual env
:: Building from an sdist is the best way to avoid installing as an EGG (installing as EGG causes
:: problems when I try to import it for pyinstaller, despite that EGG is supposed to be fully supported).
cd src/faulthandler
rmdir /S /Q build
..\..\%ENVDIR%\Scripts\python setup.py sdist --format=gztar || goto :error
..\..\%ENVDIR%\Scripts\pip install dist\faulthandler-2.3.tar.gz || goto :error
cd ..\..

:: CD to the Adept directory to install adept to the virtual environment
cd src/adept
rmdir /S /Q build
..\..\%ENVDIR%\Scripts\python setup.py install || goto :error
cd ..\..

:: Now that everything is installed, we can run the permitting project's
:: setup.py commands to build everything we want/need.
%ENVDIR%\Scripts\python src\pyinstaller\pyinstaller.py -y --onedir --noupx --icon-file=windows_build\natcap_logo.ico -c run_adept.spec || goto :error

IF NOT %BUILD_STATIC_DATA% == "true" goto :skip_big_data
%ENVDIR%\Scripts\python setup.py static_data_colombia || goto :error
:skip_big_data

IF NOT %BUILD_MAFE% == "true" goto :skip_mafe
%ENVDIR%\Scripts\python setup.py dist_colombia --nsis-dir=dist/total_coll || goto :error
:skip_mafe

IF NOT %BUILD_OPAL% == "true" goto :skip_opal
%ENVDIR%\Scripts\python setup.py dist_global --nsis-dir=dist/total_coll || goto :error
:skip_opal

goto :EOF

:error
exit /b %errorlevel%
