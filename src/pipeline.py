"""Pipeline orchestrator: raw files -> enriched, scored, search-ready leads."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import classify, cleaning, email_intel, filters, ingest, scoring

PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "leads.parquet"


def run(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Run the full enrichment pipeline on a raw concatenated DataFrame."""
    if df_raw.empty:
        return df_raw
    df = ingest.merge_and_dedupe(df_raw)
    df = cleaning.clean(df)
    df = email_intel.classify_emails(df)
    df = classify.classify_contacts(df)
    df = scoring.score_leads(df)
    df = filters.build_search_blob(df)
    return df.reset_index(drop=True)


def run_on_directory(directory: str | Path) -> pd.DataFrame:
    return run(ingest.load_directory(directory))


def save_processed(df: pd.DataFrame, path: Path = PROCESSED_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def load_processed(path: Path = PROCESSED_PATH) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_parquet(path)
    return None
