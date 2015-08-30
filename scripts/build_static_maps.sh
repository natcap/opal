#!/bin/bash
# EXECUTE THIS FROM THE PERMITTING ROOT

ENVDIR=adept_py_env_static_maps
deactivate

rm -rf build
rm -rf $ENVDIR
python bootstrap_adept_environment.py > setup_environment.py
python setup_environment.py --clear --system-site-packages $ENVDIR
source $ENVDIR/bin/activate

pushd src/invest
# IF YOU WOULD LIKE TO REBUILD ALL OF INVEST-3, UNCOMMENT THIS NEXT LINE
#hg purge  # clean out the invest-3 repo
python setup.py install

popd

# return to adept dir to build adept.
pushd src/adept
python setup.py install
popd

pushd src/pygeoprocessing
python setup.py install
popd

python scripts/build_carbon_maps.py
python scripts/build_sediment_maps.py
python scripts/build_nutrient_maps.py
