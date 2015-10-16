outname=$1
path=$2
startdir=$(pwd)
tmpdir=scan-$4
device=$3

cd $path
mkdir $tmpdir
cd $tmpdir
echo "################## Scanning ###################"
scanimage --device-name=$device -y 279.4 -x 215.9 --batch --format=tiff --mode Color --resolution 300 --source ADF
echo "############## Converting to PDF ##############"
#Use tiffcp to combine output tiffs to a single mult-page tiff
files=$(find . -type f -printf x | wc -c)
if [ $files -gt 0 ];
then
	tiffcp -c lzw out*.tif output.tif ;

#Convert the tiff to PDF
echo "Convert the tiff to PDF"
tiff2pdf output.tif > $path/$outname
fi
cd ..
echo "################ Cleaning Up ################"
rm -rf $tmpdir
