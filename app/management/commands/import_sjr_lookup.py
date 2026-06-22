import os
import re
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import SjrLookup


def normalize_issn(value):
    return str(value or "").replace("-", "").replace(" ", "").strip().upper()


def extract_year_from_name(filename):
    match = re.search(r"(19\d{2}|20\d{2})", filename)
    return match.group(1) if match else None


def normalize_columns(df):
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]
    return df


class Command(BaseCommand):
    help = "Import SJR lookup rows from parquet/csv files into DB for low-memory ISSN lookups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--parquet-dir",
            default=str(Path(settings.BASE_DIR) / "sjr_parquets"),
            help="Directory with sjr_YYYY.parquet files",
        )
        parser.add_argument(
            "--csv-dir",
            default="",
            help="Optional directory with CSV files; used when no parquet files found.",
        )
        parser.add_argument(
            "--years",
            default="",
            help="Comma-separated years to import (e.g. 2022,2023). Empty = all discovered.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing rows for imported years before inserting.",
        )

    def handle(self, *args, **options):
        parquet_dir = Path(options["parquet_dir"])
        csv_dir = Path(options["csv_dir"]) if options.get("csv_dir") else None
        replace = bool(options["replace"])

        requested_years = {
            y.strip() for y in str(options.get("years", "")).split(",") if y.strip()
        }

        file_jobs = []
        if parquet_dir.exists():
            for path in sorted(parquet_dir.glob("*.parquet")):
                year = extract_year_from_name(path.name)
                if not year:
                    continue
                if requested_years and year not in requested_years:
                    continue
                file_jobs.append(("parquet", path, year))

        if not file_jobs and csv_dir and csv_dir.exists():
            for path in sorted(csv_dir.glob("*.csv")):
                year = extract_year_from_name(path.name)
                if not year:
                    continue
                if requested_years and year not in requested_years:
                    continue
                file_jobs.append(("csv", path, year))

        if not file_jobs:
            raise CommandError("No SJR files found for import.")

        total_created = 0
        imported_years = set()

        for file_type, path, year in file_jobs:
            self.stdout.write(self.style.NOTICE(f"Reading {file_type}: {path} (year={year})"))
            if file_type == "parquet":
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(
                    path,
                    sep=";",
                    engine="python",
                    usecols=lambda col: col.lower() in [
                        "title",
                        "issn",
                        "sjr best quartile",
                        "sjr quartile",
                        "country",
                    ],
                    on_bad_lines="skip",
                )

            df = normalize_columns(df)

            quartile_column = None
            if "sjr_best_quartile" in df.columns:
                quartile_column = "sjr_best_quartile"
            elif "sjr_quartile" in df.columns:
                quartile_column = "sjr_quartile"
            if quartile_column is None:
                self.stdout.write(self.style.WARNING(f"Skipping {path.name}: missing quartile column"))
                continue

            if "issn" not in df.columns:
                self.stdout.write(self.style.WARNING(f"Skipping {path.name}: missing ISSN column"))
                continue

            rows_by_issn = {}
            for row in df.itertuples(index=False):
                row_dict = row._asdict()
                raw_issn = str(row_dict.get("issn", "") or "")
                if not raw_issn.strip():
                    continue
                title = str(row_dict.get("title", "") or "").strip() or None
                country = str(row_dict.get("country", "") or "").strip() or None
                quartile = str(row_dict.get(quartile_column, "") or "").strip() or None

                for token in raw_issn.split(","):
                    issn_norm = normalize_issn(token)
                    if not issn_norm:
                        continue
                    if issn_norm in rows_by_issn:
                        continue
                    rows_by_issn[issn_norm] = (title, country, quartile)

            if not rows_by_issn:
                self.stdout.write(self.style.WARNING(f"No valid ISSN rows in {path.name}"))
                continue

            with transaction.atomic():
                if replace:
                    SjrLookup.objects.filter(year=year).delete()

                objs = [
                    SjrLookup(
                        year=year,
                        issn_norm=issn_norm,
                        title=title,
                        country=country,
                        sjr_quartile=quartile,
                        source=path.name,
                    )
                    for issn_norm, (title, country, quartile) in rows_by_issn.items()
                ]

                created = SjrLookup.objects.bulk_create(
                    objs,
                    batch_size=5000,
                    ignore_conflicts=not replace,
                )
                total_created += len(created)
                imported_years.add(year)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Imported year {year}: candidates={len(rows_by_issn)} created={len(created)}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Years={sorted(imported_years)} total_created={total_created}"
            )
        )
