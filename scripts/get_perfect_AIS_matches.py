import os 
import sys 
import pandas as pd
import copy 
root_path = os.path.abspath(os.path.join('..'))

if root_path not in sys.path:
    sys.path.append(root_path)
from core.sentinel_downloader import get_image_AIS_pairs
dt = pd.Timedelta(seconds=59)
start_date = '2023-06-01'
end_date = '2023-06-08'
golden_gate_bbox = (-6.484680,53.215902,-4.534607,53.460255) #full ferry

res = list(get_image_AIS_pairs(golden_gate_bbox,start_date,end_date))
print(f'Images found: {len(res)}')
res = [res[0]]
for i,pair in enumerate(res):
    prefilter = copy.deepcopy(pair[1])
    target = pd.to_datetime(pair[2])
    scene = pair[0]
    # print(f'target {target}')
    pair_df = pair[1].get_full_df()
    pair_df['DTG'] = pd.to_datetime(pair_df['DTG'])
    rows = pair_df[(pair_df['DTG'] - target).abs()<dt]
    pair_df ['delta'] = (pair_df['DTG'] - target).abs()
    pair_df ['delta_bool'] = (pair_df['DTG'] - target).abs()<dt

    print(f'target {target}')
    mmsis = list(set(rows['MMSI']))
    if len(mmsis) != 0:

        print(f'{mmsis} have msgs within {dt}')

        # plot these on img
        scene.download()


        



        