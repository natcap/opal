
# CCITTRLE, CCITTFAX3, CCITTFAX4 are not actually valid compression options
# on the computer I'm working on, so they are not included in this list.
declare -a COMPRESSIONTYPES=("LZW" "PACKBITS" "DEFLATE" "NONE")

if [ -z "$1" ]
then
    echo "ERROR: Need GDAL raster as argument 1, no argument given."
    exit 1
fi

echo "Testing using file $1"
du -h $1

mkdir test_geotiffs

for compression_type in "${COMPRESSIONTYPES[@]}"
do
    filename=test_geotiffs/test_$compression_type.tif
    gdal_translate -co "COMPRESS=$compression_type" $1 $filename
    du -h $filename
done

