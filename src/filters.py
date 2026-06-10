"""Filtering engine for the dashboard.

All filters compose into a single boolean mask, so filtering 100k rows takes
a few milliseconds and charts/tables update instantly on every widget change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

SEARCH_COLUMNS = ["username", "company", "email", "designation"]


def build_search_blob(df: pd.DataFrame) -> pd.DataFrame:
    """Precompute a lowercase concatenation of the searchable columns.

    Done once after the pipeline so global search is a single .str.contains.
    """
    df = df.copy()
    blob = pd.Series("", index=df.index)
    for col in SEARCH_COLUMNS:
        if col in df.columns:
            blob = blob + " " + df[col].fillna("").astype(str).str.lower()
    df["_search"] = blob
    return df


@dataclass
class LeadFilters:
    search: str = ""
    email_types: list = field(default_factory=list)
    contact_types: list = field(default_factory=list)
    countries: list = field(default_factory=list)
    cities: list = field(default_factory=list)
    companies: list = field(default_factory=list)
    score_range: tuple = (0, 100)
    linkedin: str = "Any"        # Any / Yes / No
    students: str = "Include"    # Include / Exclude / Only
    valid_email_only: bool = False
    hide_suspicious: bool = False


def apply_filters(df: pd.DataFrame, f: LeadFilters) -> pd.DataFrame:
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)

    if f.search.strip():
        for term in f.search.lower().split():
            mask &= df["_search"].str.contains(term, regex=False)

    if f.email_types:
        mask &= df["email_type"].isin(f.email_types)
    if f.contact_types:
        mask &= df["contact_type"].isin(f.contact_types)
    if f.countries:
        mask &= df["country"].isin(f.countries)
    if f.cities:
        mask &= df["city"].isin(f.cities)
    if f.companies:
        mask &= df["company"].isin(f.companies)

    lo, hi = f.score_range
    mask &= df["lead_score"].between(lo, hi)

    if f.linkedin == "Yes":
        mask &= df["has_linkedin"]
    elif f.linkedin == "No":
        mask &= ~df["has_linkedin"]

    if f.students == "Exclude":
        mask &= ~df["student_flag"]
    elif f.students == "Only":
        mask &= df["student_flag"]

    if f.valid_email_only:
        mask &= df["email_valid"]
    if f.hide_suspicious:
        mask &= ~df["suspicious_flag"]

    return df[mask]
