import os
from pathlib import Path
from dotenv import load_dotenv

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

