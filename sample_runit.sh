#!/bin/bash

ENVDIR=adept_py_env
deactivate

rm -rf build
rm -rf $ENVDIR
python bootstrap_adept_environment.py > setup_environment.py
python setup_environment.py --clear --system-site-packages $ENVDIR
source $ENVDIR/bin/activate

pushd invest-natcap.invest-3

# IF YOU WOULD LIKE TO REBUILD ALL OF INVEST-3, UNCOMMENT THIS NEXT LINE
#hg purge  # clean out the invest-3 repo
python setup.py install

popd  # return to adept dir to build adept.
python setup.py install

