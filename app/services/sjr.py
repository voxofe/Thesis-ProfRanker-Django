from django.conf import settings

from app.models import SjrLookup

from .sjr_cache import get_sjr_data

# SJR Quartile Retrieval Logic

def _normalize_issn(value):
    return str(value or "").replace("-", "").replace(" ", "").strip().upper()


def get_sjr_quartile(year, issn, include_source=False):
    year = str(year or "").strip()
    normalized_issn = _normalize_issn(issn)
    if not year or not normalized_issn:
        return None

    if getattr(settings, "DB_SJR_LOOKUP_ENABLED", False):
        db_match = (
            SjrLookup.objects.filter(year=year, issn_norm=normalized_issn)
            .only("sjr_quartile", "title", "country")
            .first()
        )
        if db_match:
            result = {
                "sjr_quartile": db_match.sjr_quartile,
                "title": db_match.title,
                "country": db_match.country,
            }
            if include_source:
                result["lookup_source"] = "db"
            return result
        if not getattr(settings, "DB_SJR_LOOKUP_FALLBACK_TO_PARQUET", True):
            return None

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

    def issn_match(row_issn, target_issn):
        # Split on comma, normalize each, and check for match
        issn_list = [_normalize_issn(x) for x in str(row_issn).split(",")]
        return _normalize_issn(target_issn) in issn_list

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
    if include_source:
        sjr_data["lookup_source"] = "parquet"

    print(f"🏆 SJR Quartile: {journal_title} - {sjr_quartile}\n")

    return sjr_data
