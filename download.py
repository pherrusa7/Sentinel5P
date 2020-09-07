import argparse
from pathlib import Path
import pickle

import numpy as np
from sentinelsat import SentinelAPI

def set_parser():
    """ set custom parser """
    
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-c", "--city", type=str, required=True, 
                        help="City to download the data from [Moscow, Istanbul, Berlin]")
    parser.add_argument("-f", "--folder", type=str, required=True, 
                        help="Folder to save the data")
    parser.add_argument("-l", "--level", type=str, required=False, default='L2', 
                        help="L1B or L2 data")
    parser.add_argument("-q", "--quiet", required=False, default=True, action='store_false',
                        help="don't print status messages to stdout")

    return parser

def get_products(api, product, footprint, level, date_range):
        # search by polygon, time, and SciHub query keywords
        products = api.query(footprint,
                            date=(date_range[0], date_range[1]), 
                            area_relation='Intersects',
                            platformname='Sentinel-5',
                            producttype=product,
                            processinglevel=level, # L2 or L1B
                            processingmode='Offline'
                            )

        # convert to Pandas DataFrame
        products_df = api.to_dataframe(products)

        return products, products_df

def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def prepare_download(city, folder, level='L2', date_range=['20190101', '20191231']):
    """ download products defined in the bellow dict 'products' for the selected 'city'
        fill the dict 'products' from: https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-5p/products-algorithms
    """
    print(f"Downloading {level} products of {city} in {folder}")

    # set api
    api = SentinelAPI('s5pguest', 's5pguest', api_url='https://s5phub.copernicus.eu/dhus/')

    # big polys with cities inside
    polys = {'Moscow': "POLYGON((34.61091247331172 54.068784458219056,40.70616344210223 54.068784458219056,40.70616344210223 57.347572592132536,34.61091247331172 57.347572592132536,34.61091247331172 54.068784458219056))", # 1070
             'Istanbul': "POLYGON((27.36677367672644 39.90274802657737,30.299245456849114 39.90274802657737,30.299245456849114 42.53557310883875,27.36677367672644 42.53557310883875,27.36677367672644 39.90274802657737))", # 566
             'Berlin': "POLYGON((12.558777671087848 52.03654820015532,14.114302561752853 52.03654820015532,14.114302561752853 53.025487507188046,12.558777671087848 53.025487507188046,12.558777671087848 52.03654820015532))" } # 825
    
    # choose product form dict:
    # name: [name, description, user docs]
    products = {'L2':
                    {'L2__O3____': ['L2__O3____', 'Ozone (O3) total column', 'PRF-O3-NRTI, PRF-03-OFFL, PUM-O3, ATBD-O3, IODD-UPAS'], 
                    #'L2__O3_TCL': ['L2__O3_TCL', 'Ozone (O3) tropospheric column', 'PRF-03-T, PUM-O3_T, ATBD-O3_T, IODD-UPAS'],
                    #'L2__O3__PR': ['L2__O3__PR', 'Ozone (O3) profile', 'PUM-PR , ATBD-O3_PR , IODD-NL'],
                    #'L2__O3_TPR': ['L2__O3_TPR', 'Ozone (O3) tropospheric profile', 'PUM-PR , ATBD-O3_PR , IODD-NL'],
                    'L2__NO2___': ['L2__NO2___', 'Nitrogen Dioxide (NO2), total and tropospheric columns', 'PRF-NO2, PUM-NO2, ATBD-NO2, IODD-NL'],
                    'L2__SO2___': ['L2__SO2___', 'Sulfur Dioxide (SO2) total column', 'PRF-SO2, PUM-SO2, ATBD-SO2, IODD-UPAS'],
                    'L2__CO____': ['L2__CO____', 'Carbon Monoxide (CO) total column', 'PRF-CO, PUM-CO, ATBD-CO, IODD-NL'],
                    'L2__CH4___': ['L2__CH4___', 'Methane (CH4) total column', 'PRF-CH4, PUM-CH4, ATBD-CH4, IODD-NL'],
                    'L2__HCHO__': ['L2__HCHO__', 'Formaldehyde (HCHO) total column', 'PRF-HCHO, PUM-HCHO , ATBD-HCHO , IODD-UPAS'],
                    'L2__CLOUD_': ['L2__CLOUD_', 'Cloud fraction, albedo, top pressure', 'PRF-CL, PUM-CL, ATBD-CL, IODD-UPAS'],
                    'L2__AER_AI': ['L2__AER_AI', 'UV Aerosol Index', 'PRF-AI, PUM-AI, ATBD-AI, IODD-NL'],
                    'L2__AER_LH': ['L2__AER_LH', 'Aerosol Layer Height (mid-level pressure)', 'PRF-LH, PUM-LH , ATBD-LH , IODD-NL'],
                    #'UV product': ['proUV product', 'Surface Irradiance/erythemal dose', '-'],
                    #'L2__NP_BDx': ['L2__NP_BDx', 'Suomi-NPP VIIRS Clouds, x=3, 6, 7 2', 'PRF-NPP, PUM-NPP, ATBD-NPP'],
                    },
                'L1B':
                    {'L1B_RA_BD1': ['L1B_RA_BD1'], 
                    'L1B_RA_BD2': ['L1B_RA_BD2'],
                    'L1B_RA_BD3': ['L1B_RA_BD3'],
                    'L1B_RA_BD4': ['L1B_RA_BD4'],
                    'L1B_RA_BD5': ['L1B_RA_BD5'],
                    'L1B_RA_BD6': ['L1B_RA_BD6'],
                    'L1B_RA_BD7': ['L1B_RA_BD7'],
                    'L1B_RA_BD8': ['L1B_RA_BD8'],
                    'L1B_IR_UVN': ['L1B_IR_UVN'],
                    'L1B_IR_SIR': ['L1B_IR_SIR']
                    }
                }[level]

    #date_range=['20191229', '20191231']
    #products = {'L2__O3____': ['L2__O3____', 'Ozone (O3) total column', 'PRF-O3-NRTI, PRF-03-OFFL, PUM-O3, ATBD-O3, IODD-UPAS']}

    logs = {}

    footprint = polys[city]
    for product in products.keys():
        print("\n########\nCurrent product: {} | current city: {} | footprint: {}".format(product, city, footprint))
        logs[product] = {}

        # create a folder for current product
        path = '{}/{}'.format(folder, product)
        Path(path).mkdir(parents=True, exist_ok=True)

        # get links for a product & save them
        products, products_df = get_products(api, product, footprint, level, date_range)
        products_df.to_csv(folder+"/{}_{}.csv".format(city, product))
        
        # download data from linkss
        downloaded_prods, retrieval_scheduled, failed_prods = api.download_all(products, directory_path=path, n_concurrent_dl=4)
        logs[product]['downloaded_prods'] = downloaded_prods
        logs[product]['retrieval_scheduled'] = retrieval_scheduled
        logs[product]['failed_prods'] = failed_prods

    save_obj(logs, folder+"/{}_logs".format(city))
    print(logs)
        

def main():
    
    parser = set_parser()
    options = parser.parse_args()
    
    if options.quiet:
        print("Downloading data for city %s in folder %s..." % (options.city, options.folder))

    prepare_download(options.city, options.folder, options.level)

if __name__ == "__main__":
    main()

    """
    example of L1B query:
     ( footprint:"Intersects
        (POLYGON
            (
                (32.026863098144524 53.06081843472961,44.22924041748046 53.06081843472961,44.22924041748046 58.34301952407972,
                 32.026863098144524 58.34301952407972,32.026863098144524 53.06081843472961)
            )
        )" 
    ) AND 
    ( 
         beginPosition:[2019-01-01T00:00:00.000Z TO 2020-01-01T23:59:59.999Z] AND 
         endPosition:[2019-01-01T00:00:00.000Z TO 2020-01-01T23:59:59.999Z] 
    ) AND 
    ( 
        (platformname:Sentinel-5 AND producttype:L1B_RA_BD1 AND processinglevel:L1B AND processingmode:Offline)
    )

    source conda-bash
    conda activate traffic4cast20

    python download.py -c Berlin -f /iarai/public/t4c/meteosat/raw1.5/Berlin -l L1B
    python download.py -c Istanbul -f /iarai/public/t4c/meteosat/raw1.5/Istanbul -l L1B
    python download.py -c Moscow -f /iarai/public/t4c/meteosat/raw1.5/Moscow -l L1B

    """


