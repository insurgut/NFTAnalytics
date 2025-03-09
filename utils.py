import pandas as pd
import json
from datetime import datetime
from typing import List, Optional

def load_channels() -> List[str]:
    """Load telegram channels from configuration"""
    try:
        with open('channels.json', 'r') as f:
            return json.load(f)
    except:
        return ["NFTCalendar", "NFTDrops", "NFTProject"]

def save_data(data: pd.DataFrame) -> None:
    """Save parsed data to CSV file"""
    data.to_csv('nft_data.csv', index=False)

def load_data() -> Optional[pd.DataFrame]:
    """Load parsed data from CSV file"""
    try:
        data = pd.read_csv('nft_data.csv')
        data['date'] = pd.to_datetime(data['date'])
        return data
    except:
        return None
