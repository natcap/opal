#!/bin/bash -e

ENVDIR=adept_py_env

rm -rf build
rm -rf $ENVDIR
python bootstrap_adept_environment.py > setup_environment.py
python setup_environment.py --clear --system-site-packages $ENVDIR
source $ENVDIR/bin/activate

pushd invest-natcap.invest-3

# IF YOU WOULD LIKE TO REBUILD ALL OF INVEST-3, UNCOMMENT THIS NEXT LINE
hg purge  # clean out the invest-3 repo
python setup.py install
popd  # return to adept directory


echo 'Activated'
python setup.py install --no-compile
pushd test


echo "Using python " $(which python)
echo "STARTING TESTS"
pwd
timeout=600

# Can't use multiple processor cores to run tests concurrently since most
# tests write to the same directory.  Use a single process instead.
# It's necessary to declare a single process, as the process-timeout option
# only works when we specify how many processes we're using.
#processes=$(grep "^core id" /proc/cpuinfo | sort -u | wc -l)
processes=1
echo $processes

# I can't output xunit test reports with an individual process timeout.  I
# assume that the program or programmer running this test file will have a
# top-level timing mechanism.  It's a known but with nosetests.  See:
# http://stackoverflow.com/a/13306487
#run_tests="nosetests -v --logging-filter=None --process-timeout=$timeout --processes=$processes"
run_tests="nosetests -v --with-xunit --with-coverage --cover-xml --cover-tests --cover-package=adept --logging-filter=None"
test_files=""

if [ $# -eq 0 ]
# If there are no arguments, run all tests
then
    test_files=""
elif [ $1 == 'release' ]
then
# If the first argument is 'release', run the specified tests for released models.
    test_files=(
        adept_test.py
        )
    echo "Testing " ${test_files[*]}
    test_files="${test_files[*]}"
elif [ $1 == 'all' ]
then
# If the user specifies all as the first argument, run all tests
    test_files=""
else
# Otherwise, take the arguments and pass them to nosetests
    test_files="$@"
fi

${run_tests} ${test_files} 3>&1 1>&2 2>&3 | tee test_errors.log

popd
deactivate
