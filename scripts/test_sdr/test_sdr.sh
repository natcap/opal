#!/bin/bash -e

ENVDIR=adept_sdr_test_env

rm -rf build
rm -rf $ENVDIR
python bootstrap_adept_environment.py > setup_environment.py
python setup_environment.py --clear --system-site-packages $ENVDIR
source $ENVDIR/bin/activate
alias nosetests=$ENVDIR/bin/nosetests
echo "Activated!"

pushd src/invest

# IF YOU WOULD LIKE TO REBUILD ALL OF INVEST-3, UNCOMMENT THIS NEXT LINE
#hg purge  # clean out the invest-3 repo
python setup.py install
popd  

pushd src/palisades
#pushd $HOME/workspace/palisades
python setup.py install
popd

pushd src/faulthandler
python setup.py install
popd

pushd src/adept
rm -rf build
rm -rf dist
python setup.py install
popd # return to adept dir to build adept.

python scripts/test_sdr/test_sdr.py
#python scripts/test_sdr/extract_mean_sdr_under_impact.py
