import argparse
import os
import re
import sys

import pandas as pd


DEFAULT_CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "sjr_cache")
)


def infer_year_from_filename(csv_path):
    match = re.search(r"(19\d{2}|20\d{2})", os.path.basename(csv_path))
    return match.group(1) if match else None


def parquetify(csv_path, year, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"sjr_{year}.parquet")

    try:
        df = pd.read_csv(
            csv_path,
            sep=";",
            engine="python",
            usecols=lambda col: col.lower()
            in [
                "title",
                "issn",
                "sjr best quartile",
                "sjr quartile",
                "country",
            ],
            on_bad_lines="skip",
        )

        df.columns = [col.lower().replace(" ", "_") for col in df.columns]
        df.to_parquet(cache_file)
        print(f"Cached SJR data for {year} in {cache_file}")
        return df
    except Exception as exc:
        print(f"Error processing data: {exc}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Convert a Scimago SJR CSV file into a cached parquet file."
    )
    parser.add_argument("csv_path", help="Path to the downloaded SJR CSV file")
    parser.add_argument(
        "--year",
        help="Year for the SJR dataset (e.g., 2020). If omitted, inferred from filename.",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE_DIR,
        help="Directory to store cached parquet files",
    )

    args = parser.parse_args()

    year = args.year or infer_year_from_filename(args.csv_path)
    if not year:
        print("Error: year not provided and could not be inferred from filename.")
        sys.exit(1)

    parquetify(args.csv_path, year, args.cache_dir)


if __name__ == "__main__":
    main()
