
# %%

try:    
    import os
    import argparse
    from glob import iglob
    from os.path import join
    from pathlib import Path
    import pickle

    import warnings

    import xarray as xr
    import pandas as pd
    import numpy as np

    import h5py

    from termcolor import colored

    from matplotlib import pyplot as plt
    import matplotlib.colors as colors
    import matplotlib.gridspec as gridspec
    import matplotlib.patches as mpatches

    import cartopy
    import cartopy.crs as ccrs
    import cartopy.feature as cf
    from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

    print(colored("All modules loaded!\n", 'green'))
except ModuleNotFoundError:
    print(colored("Module not found: %s"%ModuleNotFoundError, 'red'))

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
    'L2__CLOUD_': { # 'cloud_fraction' doesn't need _validity, it can't be used with the current script
        'keep': 'cloud_fraction, cloud_top_pressure, cloud_top_height, cloud_base_pressure, ' +\
                'cloud_base_height, cloud_optical_depth, surface_albedo', 
        'threshold': 50},
    'L2__AER_AI': {
        'keep': 'absorbing_aerosol_index',
        'threshold': 50},
    'L2__AER_LH': {                                 # TODO
        'keep': '',
        'threshold': 50}
                }

#np.seterr('ignore')
#warnings.filterwarnings("ignore")

DEBUG = False

def set_parser():
    """ set custom parser """
    
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-c", "--city", type=str, required=True, 
                        help="City to process the data from [Moscow, Istanbul, Berlin]")
    parser.add_argument("-p", "--product", type=str, required=True, 
                        help="Product to process [\'L2__O3____\', \'L2__NO2___\', \'L2__SO2___\', \
                        \'L2__CO____\', \'L2__CH4___\', \'L2__HCHO__\', \'L2__CLOUD_\', \
                         \'L2__AER_AI\', \'L2__AER_LH\'] ")
    parser.add_argument("-f", "--folder", type=str, required=False, default='../data/final_tensors', 
                        help="Folder to save the final tensors")
    parser.add_argument("-f_grid", "--folder_grid", type=str, required=False, default='../data/crop', 
                        help="Folder with L3 processed data")
    parser.add_argument("-f_src", "--folder_src", type=str, required=False, default='../data', 
                        help="Folder with L2 S-5P original data")


    return parser

def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

def retrieve_files(city, product, folder_source, extension='.zip', verbose=True):
    # files to retrieve
    path_files = join(folder_source, city, product, '*'+extension)
    all_files = sorted(list(iglob(path_files, recursive=True)))

    if verbose:
        print("looking for files at %s"%(path_files))
        print(colored(f"number of {extension} detected: {len(all_files)}", "green"))

    return all_files

def create_folder_to_save(folder, city):
    """  This function creates a folder if not exists in 
            '{folder}/{city}/{product}'
         to store all processed files by harp
    """
    path = f'{folder}/{city}/'
    Path(path).mkdir(parents=True, exist_ok=True)

    print(f"Processed data will be stored in: {path}\n")
    
    return path

def get_time_attr_old(all_files, verbose=False):
    """ this function creates a dict with time atributes for each file """

    print(colored("loading time attributes, it can take few minutes...", 'blue'))
    attributes = {file_i.split('/')[-1]: 
                    {'time_coverage_start': xr.open_dataset(file_i).attrs['time_coverage_start'],
                    'time_coverage_end': xr.open_dataset(file_i).attrs['time_coverage_end']
                    } for file_i in all_files
                }

    if verbose:
        print('attributes:', attributes)

    return attributes

def get_time_attr(all_files, path, product, verbose=False):
    """ this function creates a dict with time atributes for each file if
        it is not already stored in disk
    """
    path_dict = create_folder_to_save(path[:-1], 'dicts')
    path_dict = f'{path_dict}{product}'

    if not os.path.isfile(path_dict+'.pkl'):
        print(colored("loading time attributes, it can take few minutes...", 'blue'))
        attributes = {file_i.split('/')[-1]: 
                        {'time_coverage_start': xr.open_dataset(file_i).attrs['time_coverage_start'],
                        'time_coverage_end': xr.open_dataset(file_i).attrs['time_coverage_end']
                        } for file_i in all_files
                    }
        # save them
        save_obj(attributes, path_dict)

    else: 
        print(colored("loading time attributes from memory...", 'blue'))
        attributes = load_obj(path_dict)

    if verbose:
        print('attributes:', attributes)

    return attributes

def read_h5(path):
    with h5py.File(path, 'r') as hf:

        # get the name of the dataset
        key = list(hf.keys())[0]

        # access to the dataset and get all data
        data = hf[key][:]
    return data

def read_product_netCDF4(product, path=f'../data/final_tensors/Moscow/'):
    ''' product should be one of the following: 
        ['L2__O3____', 'L2__NO2___', 'L2__SO2___', 'L2__CO____', 'L2__CH4___', 
        'L2__HCHO__', 'L2__CLOUD_', 'L2__AER_AI', 'L2__AER_LH'] 

        to open and test it:
        h = read_product_netCDF4(product)
        img = h['netcdf'].groupby('time.year').mean()[0]
        create_save_plot(img, 'foo')
    '''
    # declare names
    netcdf_name = f'{path}/{product}.nc'
    tensor_name = f'{path}/{product}_data.h5'
    time_name = f'{path}/{product}_time.h5'

    # read
    netcdf = xr.open_dataarray(netcdf_name)
    tensor = read_h5(tensor_name)
    time = read_h5(time_name)

    return {'data': tensor, 'time': time, 'netcdf': netcdf}

def get_tensors(no2_L3_DATA_mean):
    # get data and make longitude first: (time, lon, lat)
    tensor = no2_L3_DATA_mean.values
    tensor = np.moveaxis(tensor, 1, -1)

    # get dates and trim yyyy-mm-dd
    time_values = no2_L3_DATA_mean.coords['time'].values
    time_values = np.asarray([str(d)[:10] for d in time_values], dtype='S')

    return tensor, time_values

def save_tensors(path, product, no2_L3_DATA_mean):
    """ save tensor and its date indexes into h5 files """

    tensor, time_values = get_tensors(no2_L3_DATA_mean)

    # declare names
    netcdf_name = f'{path}{product}.nc'
    tensor_name = f'{path}{product}_data.h5'
    time_name = f'{path}{product}_time.h5'

    with h5py.File(tensor_name, 'w') as hf:
        hf.create_dataset(f'{product}_data',  data=tensor)

    with h5py.File(time_name, 'w') as hf:
        hf.create_dataset(f'{product}_time',  data=time_values)
    
    # save original netcdf file
    no2_L3_DATA_mean.to_netcdf(netcdf_name)

    print(colored(f'data saved in: {tensor_name}', 'green') )
    print(colored(f'time index saved in: {time_name}', 'green'))
    print(colored(f'original netcdf saved in {netcdf_name}', 'green'))

def create_save_plot(img, fname):
    fig = plt.figure(figsize=(18, 6))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # plot data
    im = img.plot.pcolormesh(ax=ax, x='longitude', y='latitude',
                                cmap='magma_r', add_colorbar=True, 
                                transform=ccrs.PlateCarree(), zorder=1)
    #ax.set_title('Centered in %s'%folder)

    # add backgorund features
    #ax.stock_img()
    ax.gridlines()
    state_provinces = cf.NaturalEarthFeature(category='cultural', name='admin_1_states_provinces_lines', 
                                            scale='10m', facecolor='none')
    ax.add_feature(cartopy.feature.LAND, edgecolor='black')
    ax.add_feature(state_provinces, linewidth=0.4, edgecolor='black')

    # set axis
    gl = ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.3, linestyle=':')
    gl.xlabels_top = False
    gl.ylabels_right = False
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER

    plt.savefig(fname, bbox_inches='tight')

def save_log(city, product, n_after, n_before, all_files, fname_log):
    # fill log
    cols = ['City', 'Product', 'Unique Days', 'Orbits with Data', 'Total Orbits']
    dat = [city, product, n_after, n_before, len(all_files)]
    df = pd.DataFrame([dat], columns=cols)

    # save log
    if not os.path.isfile(fname_log):
        df.to_csv(fname_log, header=True)
        print(colored(f'created log: {fname_log}', 'green'))
    else: 
        df.to_csv(fname_log, mode='a', header=False)
        print(colored(f'appended log to: {fname_log}'), 'green' )

def process(city, product, folder, folder_src, folder_grid, var_product=VAR_PRODUCT):
    """ main function to stack grids into 'time' dimension """

    #print(xr.show_versions())

    ## 1. get original files to substract time information & create a folder to store final tensors
    all_files = retrieve_files(city, product, folder_src)
    path = create_folder_to_save(folder, city)

    ## 2. create time attributes & a function to access them
    attributes = get_time_attr(all_files, path, product)
    def preprocess(ds, attributes=attributes):
        ds['time'] = pd.to_datetime(np.array([attributes[ds.attrs['source_product']]['time_coverage_start']])).values
        return ds

    ## 3. load & stack all files over time dimension
    all_files_L3 = retrieve_files(city, product, folder_grid, '.nc')
    L3_DATA = xr.open_mfdataset(all_files_L3, combine='nested', concat_dim='time', 
                            preprocess=preprocess, chunks={'time': 100})

    ## 4. group the different orbits by day
     # set all dates to have time at 00h so multiple measurements in a day have the same label
    L3_DATA.coords['time'] = L3_DATA.time.dt.floor('1D')

     # group by 'date' using an average (mean)
    L3_DATA_mean = L3_DATA.groupby('time').mean()

    ## 5. get variable of interest and annual average
    var_of_interest = var_product[product]['keep'].split(',')[0]
    no2_L3_DATA_mean = L3_DATA_mean[var_of_interest]
    year_mean = no2_L3_DATA_mean.groupby('time.year').mean()[0]

    ## 6. get info about aggregation
    n_before = L3_DATA[var_of_interest].shape[0]
    n_after = no2_L3_DATA_mean.shape[0]
    print(colored(f"--> There were {n_before} orbits belonging to {n_after} unique days.\n", 'blue'))

    ## 7. get and save tensors
    save_tensors(path, product, no2_L3_DATA_mean)

    ## 8. save a plot
    name = f'{path}/{city}_{product}.png'
    create_save_plot(year_mean, name)

    ## 9. save a log
    save_log(city, product, n_after, n_before, all_files, f'{folder}/LOG.csv')

def main():

    not_generated = []

    city, product = 'Moscow', 'L2__O3____'
    folder = '../data/final_tensors'
    folder_src = '../data'
    folder_grid =  '../data/crop'

    for city in ['Moscow', 'Istanbul', 'Berlin']:
        for product in list(VAR_PRODUCT.keys()):
            try:
                process(city, product, folder, folder_src, folder_grid)
                print("")
            except:
                not_generated.append(f'{city}/{product}')
    
    print(not_generated)
    """ 
    products that didn't have data in our area of interest:
    
    ['Moscow/L2__CO____', 'Moscow/L2__HCHO__', 'Moscow/L2__CLOUD_', 
    'Moscow/L2__AER_AI', 'Moscow/L2__AER_LH', 

    'Istanbul/L2__CO____', 'Istanbul/L2__CH4___', 'Istanbul/L2__CLOUD_', 
    'Istanbul/L2__AER_AI', 'Istanbul/L2__AER_LH',

    'Berlin/L2__CO____', 'Berlin/L2__CLOUD_', 'Berlin/L2__AER_AI', 
    'Berlin/L2__AER_LH']
    """


# %%
main()