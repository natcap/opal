SET ENVDIR=invest_python_environment
DEL /S /Q build
DEL /S /Q %ENVDIR%
python bootstrap_adept_environment.py > setup_environment.py
python setup_environment.py --clear --system-site-packages %ENVDIR%
copy C:\Python27\Lib\distutils\distutils.cfg .\%ENVDIR%\Lib\distutils\distutils.cfg

cd invest-natcap.invest-3
..\%ENVDIR%\Scripts\python setup.py install
cd ..

%ENVDIR%\Scripts\python setup.py install

%ENVDIR%\Scripts\python run_adept.py

::%ENVDIR%\Scripts\python invest_nutrient.py
::%ENVDIR%\Scripts\python invest_wave_energy.py
::%ENVDIR%\Scripts\python invest_marine_water_quality_biophysical.py
::%ENVDIR%\Scripts\python invest_overlap_analysis.py
::%ENVDIR%\Scripts\python invest_biodiversity_biophysical.py
::%ENVDIR%\Scripts\python invest_wind_energy.py