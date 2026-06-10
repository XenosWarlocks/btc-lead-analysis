"""Data cleaning: normalization of names, titles, companies, countries,
plus validity flags for emails/mobiles and a suspicious-record flag."""
from __future__ import annotations

import re

import pandas as pd

from .config import (
    COMPANY_LEGAL_SUFFIXES,
    COUNTRY_ALIASES,
    EMAIL_REGEX,
    PHONE_COUNTRY_CODES,
    TITLE_ABBREVIATIONS,
)
from .ingest import PLACEHOLDER_VALUES

_WS = re.compile(r"\s+")
_EMAIL_RE = re.compile(EMAIL_REGEX)


def _blank_placeholders(series: pd.Series) -> pd.Series:
    """Replace placeholder junk ('0', 'n/a', '0000-00-00', ...) with NA."""
    s = series.fillna("").astype(str).str.strip()
    s = s.map(lambda v: _WS.sub(" ", v))
    return s.mask(s.str.lower().isin(PLACEHOLDER_VALUES) | (s == ""))


def normalize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and null-out placeholders across the string columns."""
    df = df.copy()
    for col in ("username", "email", "designation", "company", "country",
                "city", "linkedin", "instagram", "twitter", "mobile",
                "country_code", "dob", "interest", "interests"):
        if col in df.columns:
            df[col] = _blank_placeholders(df[col])
        else:
            df[col] = pd.NA
    return df


def normalize_company(name: str | float) -> str:
    """Build a matching key: lowercase, no punctuation, legal suffixes removed.

    'Ioncares Co.,Ltd' and 'IonCares Co., Ltd.' both become 'ioncares'.
    """
    if pd.isna(name):
        return ""
    s = str(name).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = _WS.sub(" ", s).strip()
    changed = True
    while changed:  # peel stacked suffixes ("pvt ltd", then "tech", ...)
        changed = False
        for suffix in COMPANY_LEGAL_SUFFIXES:
            suffix_clean = re.sub(r"[^\w\s]", " ", suffix)
            suffix_clean = _WS.sub(" ", suffix_clean).strip()
            if s.endswith(" " + suffix_clean):
                s = s[: -len(suffix_clean) - 1].strip()
                changed = True
    return s


def normalize_designation(title: str | float) -> str:
    """Lowercase, strip punctuation, expand abbreviations (sr -> senior)."""
    if pd.isna(title):
        return ""
    s = str(title).lower()
    s = re.sub(r"[/&,+]", " ", s)
    s = re.sub(r"[^\w\s.\-]", " ", s)
    tokens = []
    for tok in _WS.sub(" ", s).strip().split(" "):
        bare = tok.strip(".-")
        tokens.append(TITLE_ABBREVIATIONS.get(tok, TITLE_ABBREVIATIONS.get(bare, bare)))
    return " ".join(t for t in tokens if t)


def normalize_country(df: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize country names; derive from phone country_code if missing."""
    df = df.copy()

    def canon(value):
        if pd.isna(value):
            return pd.NA
        key = str(value).strip().lower()
        return COUNTRY_ALIASES.get(key, str(value).strip().title())

    country = df["country"].map(canon)

    code = df["country_code"].fillna("").astype(str)
    code = code.str.replace(r"[^\d]", "", regex=True).str.lstrip("0")
    derived = code.map(PHONE_COUNTRY_CODES)

    df["country"] = country.fillna(derived)
    df["city"] = df["city"].map(lambda v: pd.NA if pd.isna(v) else str(v).strip().title())
    return df


def add_validity_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    email = df["email"].fillna("").astype(str).str.strip().str.lower()
    df["email"] = email.mask(email == "")
    df["email_valid"] = email.map(lambda e: bool(_EMAIL_RE.match(e)))

    digits = df["mobile"].fillna("").astype(str).str.replace(r"\D", "", regex=True)
    # A real subscriber number has 7-15 digits and isn't one repeated digit.
    df["mobile_valid"] = (
        digits.str.len().between(7, 15)
        & ~digits.str.fullmatch(r"(\d)\1*").fillna(False)
    )

    df["has_linkedin"] = df["linkedin"].notna()
    return df


def add_suspicious_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Flag records that look like junk/test entries.

    Suspicious when 2+ of these hold: invalid email, invalid mobile,
    missing name, missing both company and designation, name is gibberish
    (no vowels / repeated chars), or the interest field holds a different
    email address (sign of column shifting in the source export).
    """
    df = df.copy()
    name = df["username"].fillna("").astype(str).str.strip()

    no_name = name == ""
    gibberish = name.str.len().ge(4) & ~name.str.lower().str.contains(
        r"[aeiou]", regex=True
    )
    no_role_info = df["company"].isna() & df["designation"].isna()

    interest = df["interest"].fillna("").astype(str).str.strip().str.lower()
    shifted = interest.str.contains("@", regex=False) & (interest != df["email"].fillna(""))

    signals = (
        (~df["email_valid"]).astype(int)
        + (~df["mobile_valid"]).astype(int)
        + no_name.astype(int)
        + gibberish.astype(int)
        + no_role_info.astype(int)
        + shifted.astype(int)
    )
    df["suspicious_flag"] = signals >= 2
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full cleaning stage."""
    df = normalize_text_columns(df)
    df = normalize_country(df)
    df = add_validity_flags(df)
    df["company_norm"] = df["company"].map(normalize_company)
    df["designation_norm"] = df["designation"].map(normalize_designation)
    df = add_suspicious_flag(df)
    return df
