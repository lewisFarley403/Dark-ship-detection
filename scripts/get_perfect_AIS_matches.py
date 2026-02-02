import os 
import sys 
root_path = os.path.abspath(os.path.join('..'))

if root_path not in sys.path:
    sys.path.append(root_path)
from core.sentinel_downloader import get_image_AIS_pairs

start_date = '2023-06-01'
end_date = '2023-06-30'
golden_gate_bbox = (-6.484680,53.215902,-4.534607,53.460255) #full ferry

res = get_image_AIS_pairs(golden_gate_bbox,start_date,end_date)

for pair in res:
    print('date obj ',pair[2])
    new_df = pair[1].filter_cols(lambda row: row['DTG'] == pair[2])
    print(len(new_df))
    print(new_df.get_full_df().head()['DTG'])