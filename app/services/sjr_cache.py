import pandas as pd
import requests
from io import BytesIO
import time
import os


CACHE_DIR = "sjr_cache"  # Create a directory to store cached files
os.makedirs(CACHE_DIR, exist_ok=True)

def journal_url(year):
    return f"https://www.scimagojr.com/journalrank.php?&year={year}&type=j&out=xls"

def get_sjr_data(year):
    # Fetch and cache SJR data for the given year
    cache_file = f"{CACHE_DIR}/sjr_{year}.parquet"

    # Check if data is already cached
    if os.path.exists(cache_file):
        print(f"💾 Loading cached SJR data for {year} from {cache_file}")
        return pd.read_parquet(cache_file)
    
    url = journal_url(year)
    print(f"\n📥 Downloading data from: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    start_time = time.time()
    response = requests.get(url, headers=headers)
    end_time = time.time()
    execution_time = end_time - start_time

    if response.status_code != 200:
        print(f"❌ Failed to download data, status code: {response.status_code}")
        return None  

    try:
        print(f"📑 Downloaded data in {execution_time:.4f} seconds. Now prosessing data...")
        df = pd.read_csv(
            BytesIO(response.content),
            sep=";",
            engine="python",
            usecols=lambda col: col.lower() in ["title", "issn", "sjr best quartile", "sjr quartile", "country"],
            on_bad_lines="skip"
        )

        # Normalize column names
        df.columns = [col.lower().replace(" ", "_") for col in df.columns]

        # Cache the data as parquet for faster access
        df.to_parquet(cache_file)
        print(f"💾 Cached data for {year} in {cache_file}")

        return df

    except Exception as e:
        print(f"❌ Error processing data: {e}")
        return None
