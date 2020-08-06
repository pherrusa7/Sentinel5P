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
