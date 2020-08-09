

try:    
    import argparse
    from glob import iglob
    from os.path import join
    from pathlib import Path
    import pickle

    import harp
    import numpy as np

    from termcolor import colored

    print(colored("All modules loaded!", 'green'))
except ModuleNotFoundError:
    print(colored("Module not found: %s"%ModuleNotFoundError, 'red'))

# use this flag to use only 'N_debug' days
DEBUG = False
N_debug = 10

# define harp products of each variable:
# 'keep' first value should be the variable of interest for the product
# (the one that harp has a _validity parameter)
# 'thereshold' is the minimum quality for the values to keep them
# product's 'keep' are based on Google Earth Engine L3 products:
# https://developers.google.com/earth-engine/datasets/catalog/sentinel-5p
VAR_PRODUCT = { 
    'L2__O3____': {
        'keep': 'O3_column_number_density, O3_effective_temperature',
        'threshold': 50},
    'L2__NO2___': {
        'keep': 'tropospheric_NO2_column_number_density, NO2_column_number_density,' +\
                'stratospheric_NO2_column_number_density,' +\
                'NO2_slant_column_number_density, tropopause_pressure, absorbing_aerosol_index',
        'threshold': 50},
    'L2__SO2___': {
        'keep': 'SO2_column_number_density, SO2_column_number_density_amf, ' +\
                'SO2_slant_column_number_density, absorbing_aerosol_index',
        'threshold': 50},
    'L2__CO____': {
        'keep': 'CO_column_number_density, H2O_column_number_density',
        'threshold': 50},
    'L2__CH4___': {
        'keep': 'CH4_column_volume_mixing_ratio_dry_air, aerosol_height, aerosol_optical_depth',
        'threshold': 50},
    'L2__HCHO__': {
        'keep': 'tropospheric_HCHO_column_number_density, tropospheric_HCHO_column_number_density_amf, ' +\
                'HCHO_slant_column_number_density',
        'threshold': 50},
    'L2__CLOUD_': {
        'keep': 'cloud_fraction, cloud_top_pressure, cloud_top_height, cloud_base_pressure, ' +\
                'cloud_base_height, cloud_optical_depth, surface_albedo', # cloud_fraction doen's need _validity
        'threshold': 50},
    'L2__AER_AI': {
        'keep': 'absorbing_aerosol_index',
        'threshold': 50},
    'L2__AER_LH': {                                 # TODO
        'keep': '',
        'threshold': 50}
                }

KEEP_GENERAL = 'latitude_bounds, longitude_bounds, latitude, longitude, '\
             + 'cloud_fraction, sensor_altitude, sensor_azimuth_angle, sensor_zenith_angle, '\
             + 'solar_azimuth_angle, solar_zenith_angle'

def set_parser():
    """ set custom parser """
    
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-c", "--city", type=str, required=True, 
                        help="City to process the data from [Moscow, Istanbul, Berlin]")
    parser.add_argument("-p", "--product", type=str, required=True, 
                        help="Product to process [\'L2__O3____\', \'L2__NO2___\', \'L2__SO2___\', \
                        \'L2__CO____\', \'L2__CH4___\', \'L2__HCHO__\', \'L2__CLOUD_\', \
                         \'L2__AER_AI\', \'L2__AER_LH\'] ")
    parser.add_argument("-f", "--folder", type=str, required=False, default='../data/crop', 
                        help="Folder to save the data")
    parser.add_argument("-f_src", "--folder_src", type=str, required=False, default='../data', 
                        help="Folder with L2 S-5P data")
    parser.add_argument("-d", "--degrees", type=float, required=False, default=0.01, 
                        help="pixel degrees for the grid")

    return parser

def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def get_city_bbox(city):
    """ min lat, max lat, min lon, max lon """

    if city == 'Istanbul':
        city_bbox = [40.81000, 41.30500, 28.79400, 29.23000]
    elif city == 'Moscow':
        city_bbox = [55.50600, 55.94200, 37.35700, 37.85400]
    elif city == 'Berlin':
        city_bbox = [52.35900, 52.85400, 13.18900, 13.62500]
    else:
        raise Exception('city {} is not defined'.format(city))
    
    d = {}
    d['min_lat'] = city_bbox[0]
    d['max_lat'] = city_bbox[1]
    d['min_lon'] = city_bbox[2]
    d['max_lon'] = city_bbox[3]

    return d

def bounding_box_steps(city, degrees, verbose=True):
    """ get the latitude/longitude steps to be done in a given bounding box
        and the degrees for step 
    """
    city_latlons = get_city_bbox(city)

    # compute the steps
    lon_steps = (city_latlons['max_lon'] - city_latlons['min_lon'])/degrees
    lat_steps = (city_latlons['max_lat'] - city_latlons['min_lat'])/degrees
    lat_steps, lon_steps = int(np.ceil(lat_steps)), int(np.ceil(lon_steps))

    if verbose:
        print(city_latlons['max_lat'], city_latlons['min_lat'] + degrees*lat_steps)
        print(city_latlons['max_lon'], city_latlons['min_lon'] + degrees*lon_steps)

    return lat_steps, lon_steps, city_latlons

def retrieve_files(city, product, folder_source, verbose=True):
    # files to retrieve
    path_files = join(folder_source, city, product, '*')
    all_files = sorted(list(iglob(path_files, recursive=True)))

    if verbose:
        print("looking for files at %s"%(path_files))
        print(colored("number of .nc detected: %i"%len(all_files), "green"))

    return all_files

def create_folder_to_save(folder, city, product):
    """  This function creates a folder if not exists in 
            '{folder}/{city}/{product}'
         to store all processed files by harp
    """
    path = '{}/{}/{}/'.format(folder, city, product)
    Path(path).mkdir(parents=True, exist_ok=True)

    fail_path = '{}{}'.format(path, 'files_no_data')

    print("\nfiles with no data will be saved in: {fail_path}.pkl")
    print(f"Processed data will be stored in: {path}\n")
    
    return path, fail_path

def get_harp_operations(city, product, degrees, verbose=True, 
                        var_product=VAR_PRODUCT, keep_general=KEEP_GENERAL):
    """ get the operations that harp library needs to create the grid """

    # get bounding box params & harp main variable
    lat_steps, lon_steps, city_latlons = bounding_box_steps(city, degrees)
    var_of_interest = var_product[product]['keep'].split(',')[0]

    # define harp operations
    ops_string = f"{var_of_interest}_validity > {var_product[product]['threshold']}; \
        derive(datetime_stop {{time}});\
        latitude >= {city_latlons['min_lat']-1} [degree_north] ; latitude <= {city_latlons['max_lat']+1} [degree_north] ;\
        longitude >= {city_latlons['min_lon']-1} [degree_east] ; longitude <= {city_latlons['max_lon']+1} [degree_east];\
        bin_spatial({lat_steps+1}, {city_latlons['min_lat']}, {degrees}, {lon_steps+1}, {city_latlons['min_lon']}, {degrees});\
        derive(latitude {{latitude}}); derive(longitude {{longitude}});\
        keep({var_product[product]['keep']}, {keep_general})"

    if verbose:
        print('operations:\n', ops_string, '\n')

    return ops_string

def process(city, product, degrees, folder, folder_src):
    """ """
    no_data_files = []

    ## 1. get all files to be processed & create a folder to store data
    all_files = retrieve_files(city, product, folder_src)
    path, fail_path = create_folder_to_save(folder, city, product)

    ## 2. get harp operations
    ops_string = get_harp_operations(city, product, degrees)

    if DEBUG:
        print("######## DEBUG MODE ON")
        all_files = all_files[:N_debug]

    for i, one_file in enumerate(all_files):
        try:
            print(f'{i+1}/{len(all_files)}: ', one_file)
            harp_L2_L3 = harp.import_product(one_file, operations=ops_string)
            export_pat = '{}{}.{}'.format(path, one_file.split("/")[-1].replace('L2', 'L3').split('.')[0], 'nc')
            print(f"exporting {export_pat} ...\n")
            harp.export_product(harp_L2_L3, export_pat, file_format='netcdf')
        except:
            no_data_files.append(one_file)

    save_obj(no_data_files, fail_path)
    print("files with no data:\n", no_data_files)

def main():

    parser = set_parser()
    options = parser.parse_args()
    
    process(options.city, options.product, options.degrees, options.folder, options.folder_src)

if __name__ == "__main__":
    main()

    """
    source conda-bash
    conda activate air

    Calls that we used:
    python mk_raster.py -c Moscow -p L2__NO2___
    python mk_raster.py -c Moscow -p L2__O3____
    python mk_raster.py -c Moscow -p L2__SO2___
    python mk_raster.py -c Moscow -p L2__CO____
    python mk_raster.py -c Moscow -p L2__CH4___
    python mk_raster.py -c Moscow -p L2__HCHO__

    python mk_raster.py -c Istanbul -p L2__NO2___
    python mk_raster.py -c Istanbul -p L2__O3____
    python mk_raster.py -c Istanbul -p L2__SO2___
    python mk_raster.py -c Istanbul -p L2__CO____
    python mk_raster.py -c Istanbul -p L2__CH4___
    python mk_raster.py -c Istanbul -p L2__HCHO__

    python mk_raster.py -c Berlin -p L2__NO2___
    python mk_raster.py -c Berlin -p L2__O3____
    python mk_raster.py -c Berlin -p L2__SO2___
    python mk_raster.py -c Berlin -p L2__CO____
    python mk_raster.py -c Berlin -p L2__CH4___
    python mk_raster.py -c Berlin -p L2__HCHO__
    """


