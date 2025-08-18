import pandas as pd
from .sjr_cache import get_sjr_data  

def get_sjr_quartile(year, issn):
    
    df = get_sjr_data(year)
    if df is None:
        return None 

    # Identify the correct quartile column
    quartile_column = None
    if "sjr_best_quartile" in df.columns:
        quartile_column = "sjr_best_quartile"
    elif "sjr_quartile" in df.columns:
        quartile_column = "sjr_quartile"

    if quartile_column is None:
        print("❌ Error: Could not detect 'SJR Quartile' column.")
        return None  

    # Ensure ISSN is a string and handle empty ISSN cases
    df["issn"] = df["issn"].astype(str)
    if not issn.strip():
        print(f"⚠️ Empty ISSN provided. Skipping ISSN search.")
        return None

    def normalize_issn(issn):
        return issn.replace("-", "").replace(" ", "").strip().upper()

    def issn_match(row_issn, target_issn):
        # Split on comma, normalize each, and check for match
        issn_list = [normalize_issn(x) for x in str(row_issn).split(",")]
        return normalize_issn(target_issn) in issn_list

    # Search for the ISSN
    print(f"🔎 Now searching for ISSN...")
    result = df[df["issn"].apply(lambda x: issn_match(x, issn))]

    if result.empty:
        print(f"❌ ISSN '{issn}' not found in the '{year}' dataset.\n")
        return None
    else:
        print(f"✅ ISSN '{issn}' found in the '{year}' dataset!")

    # Extract the SJR Data
    sjr_quartile = result.iloc[0][quartile_column]
    journal_title = result.iloc[0]["title"]
    country = result.iloc[0]["country"]

    sjr_data = {
        "sjr_quartile": sjr_quartile,
        "title": journal_title,   
        "country": country,
    }

    print(f"🏆 SJR Quartile: {journal_title} - {sjr_quartile}\n")

    return sjr_data
