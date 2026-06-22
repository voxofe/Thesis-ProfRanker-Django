import os
import threading
from io import BytesIO

import pandas as pd
from django.conf import settings
from django.core.files.storage import default_storage

# SJR static parquet loading.
# - Development: local filesystem under BASE_DIR/sjr_parquets
# - Production (USE_S3_MEDIA=True): same bucket/storage backend as documents (R2)

PARQUET_DIR_NAME = "sjr_parquets"
_parquet_cache = {}
_parquet_cache_lock = threading.Lock()


def _normalize_columns(df):
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]
    return df


def _local_parquet_path(year):
    return os.path.join(str(settings.BASE_DIR), PARQUET_DIR_NAME, f"sjr_{year}.parquet")


def _r2_parquet_key(year):
    return f"{PARQUET_DIR_NAME}/sjr_{year}.parquet"


def _load_local_parquet(year):
    parquet_path = _local_parquet_path(year)
    if not os.path.exists(parquet_path):
        print(f"SJR parquet not found locally for {year}: {parquet_path}")
        return None

    print(f"Loading local SJR parquet for {year} from {parquet_path}")
    df = pd.read_parquet(parquet_path)
    return _normalize_columns(df)


def _load_r2_parquet(year):
    key = _r2_parquet_key(year)
    if not default_storage.exists(key):
        print(f"SJR parquet not found in R2 for {year}: {key}")
        return None

    print(f"Loading SJR parquet for {year} from R2 key: {key}")
    with default_storage.open(key, "rb") as f:
        payload = f.read()
    df = pd.read_parquet(BytesIO(payload))
    return _normalize_columns(df)


def get_sjr_data(year):
    if year is None:
        return None

    year = str(year).strip()
    if not year:
        return None

    with _parquet_cache_lock:
        if year in _parquet_cache:
            return _parquet_cache[year]

    loader = _load_r2_parquet if settings.USE_S3_MEDIA else _load_local_parquet
    df = loader(year)
    if df is None:
        return None

    with _parquet_cache_lock:
        _parquet_cache[year] = df
    return df
