#!/bin/bash -e
#
#  Take relevant outputs from the watershed dir at arg1 and zip them up.
#

TMPDIR=_tmp_ws_outputs

rm -rf $TMPDIR
mkdir $TMPDIR


IMPACT_DIR=$1/random_impact_0

# grab the impact site vector
cp $IMPACT_DIR/impact_0.* $TMPDIR

# grab the impact USLE, SDR, sed_export rasters
cp $IMPACT_DIR/intermediate/sdr_factor.tif $TMPDIR/impact_sdr_factor.tif
cp $IMPACT_DIR/output/sed_export.tif $TMPDIR/impact_sed_export.tif
cp $IMPACT_DIR/output/usle.tif $TMPDIR/impact_usle.tif

cp $1/watershed_base_sdr.tif $TMPDIR/base_sdr_factor.tif
cp $1/watershed_base_sed_exp.tif $TMPDIR/base_sed_export.tif
cp $1/watershed_usle.tif $TMPDIR/base_usle.tif

WS_OUTPUTS=$TMPDIR/impact_ws_outputs
mkdir $WS_OUTPUTS
cp $IMPACT_DIR/output/watershed_outputs.* $WS_OUTPUTS

BASE_DIR=`basename $1`
IMPACT=`basename $IMPACT_DIR | egrep -o '[0-9]+$'`
ZIPNAME=$BASE_DIR-impact_$IMPACT.zip
zip -r $ZIPNAME $TMPDIR

echo Zipfile saved to `pwd`/$ZIPNAME
