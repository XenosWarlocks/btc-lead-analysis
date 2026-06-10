"""Data ingestion: load CSV/Excel files, canonicalize columns, merge, dedupe."""
from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

# Aliases mapping messy header variants to the canonical column names.
COLUMN_ALIASES = {
    "user_id": "user_id", "userid": "user_id", "id": "user_id",
    "username": "username", "user_name": "username", "name": "username",
    "full_name": "username", "fullname": "username", "contact_name": "username",
    "email": "email", "e-mail": "email", "email_address": "email",
    "emailid": "email", "email_id": "email", "mail": "email",
    "dob": "dob", "date_of_birth": "dob",
    "interest": "interest", "interests": "interests",
    "country_code": "country_code", "countrycode": "country_code",
    "phone_code": "country_code", "isd_code": "country_code",
    "mobile": "mobile", "phone": "mobile", "mobile_number": "mobile",
    "phone_number": "mobile", "contact_number": "mobile",
    "country": "country", "nation": "country",
    "city": "city", "town": "city", "location": "city",
    "designation": "designation", "title": "designation",
    "job_title": "designation", "jobtitle": "designation", "role": "designation",
    "position": "designation",
    "company": "company", "organisation": "company", "organization": "company",
    "company_name": "company", "employer": "company", "org": "company",
    "pincode": "pincode", "zip": "pincode", "zipcode": "pincode",
    "postal_code": "pincode",
    "ran": "ran",
    "linkedin": "linkedin", "linkedin_url": "linkedin",
    "instagram": "instagram", "instagram_url": "instagram",
    "twitter": "twitter", "twitter_url": "twitter", "x": "twitter",
}

# Fields that count toward record completeness (used to pick the best
# duplicate and shown on the dashboard as profile completeness).
COMPLETENESS_FIELDS = [
    "username", "email", "mobile", "country", "city",
    "designation", "company", "linkedin",
]

PLACEHOLDER_VALUES = {
    "", "0", "0000-00-00", "n/a", "na", "none", "null", "nil", "-", "--",
    "unknown", "not available", "xxx", "test", ".",
}


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        key = re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")
        if key in COLUMN_ALIASES:
            target = COLUMN_ALIASES[key]
            if target not in rename.values():
                rename[col] = target
    df = df.rename(columns=rename)
    # Keep only the first occurrence of each canonical column.
    return df.loc[:, ~df.columns.duplicated()]


def _read_csv_robust(source) -> pd.DataFrame:
    """Read a CSV trying multiple encodings; skip malformed lines."""
    last_err = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            if isinstance(source, (str, Path)):
                return pd.read_csv(source, dtype=str, encoding=enc,
                                   on_bad_lines="skip", skipinitialspace=True)
            source.seek(0)
            return pd.read_csv(source, dtype=str, encoding=enc,
                               on_bad_lines="skip", skipinitialspace=True)
        except (UnicodeDecodeError, pd.errors.ParserError) as err:
            last_err = err
    raise ValueError(f"Could not parse CSV: {last_err}")


def load_file(source, name: str | None = None) -> pd.DataFrame:
    """Load one CSV or Excel file (path or file-like) into a string DataFrame.

    Excel workbooks are read sheet by sheet and concatenated.
    """
    fname = name or (str(source) if isinstance(source, (str, Path)) else "upload")
    suffix = Path(fname).suffix.lower()

    if suffix in (".xlsx", ".xls", ".xlsm"):
        sheets = pd.read_excel(source, sheet_name=None, dtype=str)
        frames = [_canonicalize_columns(s) for s in sheets.values() if not s.empty]
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    else:
        df = _canonicalize_columns(_read_csv_robust(source))

    df["source_file"] = Path(fname).name
    return df


def load_uploaded(uploaded_file) -> pd.DataFrame:
    """Load a Streamlit UploadedFile."""
    data = io.BytesIO(uploaded_file.getvalue())
    return load_file(data, name=uploaded_file.name)


def load_directory(directory: str | Path) -> pd.DataFrame:
    """Load and concatenate every CSV/Excel file in a directory."""
    directory = Path(directory)
    frames = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() in (".csv", ".xlsx", ".xls", ".xlsm"):
            frames.append(load_file(path))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _completeness(df: pd.DataFrame) -> pd.Series:
    """Fraction (0-1) of key fields that hold a real (non-placeholder) value."""
    score = pd.Series(0, index=df.index, dtype=float)
    present_fields = [f for f in COMPLETENESS_FIELDS if f in df.columns]
    for field in present_fields:
        vals = df[field].fillna("").astype(str).str.strip().str.lower()
        score += (~vals.isin(PLACEHOLDER_VALUES)).astype(float)
    return score / max(len(present_fields), 1)


def merge_and_dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate, keeping the most complete record per contact.

    Primary key: lowercased email. Records without a usable email fall back
    to (name, mobile).
    """
    if df.empty:
        return df

    df = df.copy()
    df["completeness"] = _completeness(df)

    email_key = df.get("email", pd.Series("", index=df.index))
    email_key = email_key.fillna("").astype(str).str.strip().str.lower()
    has_email = email_key.str.contains("@", regex=False)

    df["_email_key"] = email_key
    df = df.sort_values("completeness", ascending=False, kind="stable")

    has_email = has_email.reindex(df.index)
    with_email = df[has_email].drop_duplicates("_email_key")

    no_email = df[~has_email].copy()
    if not no_email.empty:
        name = no_email.get("username", pd.Series("", index=no_email.index))
        mobile = no_email.get("mobile", pd.Series("", index=no_email.index))
        no_email["_fallback_key"] = (
            name.fillna("").astype(str).str.strip().str.lower() + "|" +
            mobile.fillna("").astype(str).str.replace(r"\D", "", regex=True)
        )
        keyed = no_email["_fallback_key"] != "|"
        no_email = pd.concat([
            no_email[keyed].drop_duplicates("_fallback_key"),
            no_email[~keyed],  # nothing to key on; keep as-is
        ])
        no_email = no_email.drop(columns="_fallback_key")

    merged = pd.concat([with_email, no_email], ignore_index=True)
    return merged.drop(columns=["_email_key"], errors="ignore")
