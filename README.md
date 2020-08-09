# Sentinel5P
Some scripts that help you downloading and processing satellite data from L2 to L3 products form Sentinel-5P mission:  

"perform atmospheric measurements with high spatio-temporal resolution, to be used for air quality, ozone &amp; UV radiation, and climate monitoring &amp; forecasting."  

Note that L2 products are processed measurements provided by [ESA](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-5p) and L3 are the projection of these measurements into a common grid  or [raster](https://desktop.arcgis.com/en/arcmap/10.3/manage-data/raster-and-images/what-is-raster-data.htm)

## Download Data
Sentinel-5P data need a user and password but by August 2020 it is still only a guest one: s5pguest/s5pguest

To download automatically all products available for a certain region, add the region to the dict called `polys` in function `prepare_download` and use the following syntax:
```
python download.py [-h] -c CITY -f FOLDER
```
where `CITY` is the key of the dict in the added region and `FOLDER` is the path to save the data

Unfortunately, The commented products in the dict called `products` in function `prepare_download` did not download successfully.

## Processing Data with harp: Cropping and creating a common grid
The downloaded data consist of the orbit of the satellite when it passes the specified region. Thus, it contains much more spatial information than the one we are interested in. Furthermore, the locations in the array containing the measurements are not always the same, which means that we want further process the data to have a common grid always representing the same latitude and longitudes.

The following script uses the library [Harp](http://stcorp.github.io/harp/doc/html/python.html) to filter our area of interest and create a common grid between different dates and products.
```
python mk_raster.py [-h] -c CITY -p PRODUCT [-f FOLDER] [-f_src FOLDER_SRC] [-d DEGREES]
```
Where `CITY` should be a folder containing the former downloaded data in a city under the parent folder `FOLDER_SRC` (by default `../data`). `PRODUCT` should be one of the downloaded products (e.g., L2__O3____, L2__NO2___, etc.). Finally, `FOLDER`is the target directory to save the processed data by harp (by default it is `../data/crop`). Use `DEGREES` to set the spatial cover of each pixel (by default is set to [0.01~1110m](https://www.usna.edu/Users/oceano/pguth/md_help/html/approx_equivalents.htm#:~:text=1%C2%B0%20%3D%20111%20km%20(or,0.001%C2%B0%20%3D111%20m) )).

Note that the name of the main variable for each of the products is not the same in the data provided by Sentinel-5P and `Harp` products. To find the corresponding names one should check the specific documentation of [S5P in Harp's library](http://stcorp.github.io/harp/doc/html/ingestions/index.html#sentinel-5p-products) or follow the variables that [Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/sentinel-5p) uses when converting L2 products to L3 also using `Harp`. As an example, in S5P data, the variable called `nitrogendioxide_tropospheric_column` of `L2__NO2___` product is called `tropospheric_NO2_column_number_density` in `Harp`.
