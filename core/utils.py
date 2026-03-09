import os
from pathlib import Path,PosixPath
from dotenv import load_dotenv
from yaml import safe_load

def load_sentinel_creds():
    root_dir = Path(__file__).resolve().parent.parent 
    env_path = root_dir / '.env'
    load_dotenv(dotenv_path=env_path)
    
    SH_CLIENT_ID = os.getenv("SH_CLIENT_ID")
    SH_CLIENT_SECRET = os.getenv("SH_CLIENT_SECRET")
    INSTANCE_ID = os.getenv('INSTANCE_ID')
    
    if not SH_CLIENT_ID or not SH_CLIENT_SECRET or not INSTANCE_ID:
        raise ValueError("Sentinel Hub credentials missing from .env file!")
    return SH_CLIENT_ID, SH_CLIENT_SECRET,INSTANCE_ID

def get_data_path()->PosixPath:
    root_dir = Path(__file__).resolve().parent.parent 
    yaml_dir = root_dir / 'config.yaml'
    with open(yaml_dir) as f:
        yaml_str = f.read()
        data = safe_load(yaml_str)
    system = data['current_sys']
    path = data[system]['data_path']
    is_relative = data[system]['is_relative']
    if is_relative:
        return root_dir/path
    return Path(path)
def parse_datetime_to_str(date):
    return date.strftime('%Y-%m-%d')

