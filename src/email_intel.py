"""Email intelligence: domain extraction and corporate/personal typing."""
from __future__ import annotations

import pandas as pd

from .config import (
    ACADEMIC_DOMAIN_PATTERNS,
    DISPOSABLE_EMAIL_DOMAINS,
    PERSONAL_EMAIL_DOMAINS,
)


def classify_emails(df: pd.DataFrame) -> pd.DataFrame:
    """Add email_domain, email_type, is_academic_email, is_disposable_email.

    email_type:
      - Personal : free webmail providers (gmail, yahoo, naver, ...)
      - Corporate: any other valid, non-disposable, non-academic domain
      - Academic : university domains (.edu, .ac.in, ...)
      - Unknown  : missing or invalid email
    """
    df = df.copy()

    email = df["email"].fillna("").astype(str).str.strip().str.lower()
    domain = email.str.extract(r"@([\w.\-]+)$", expand=False).fillna("")
    df["email_domain"] = domain.mask(domain == "")

    is_personal = domain.isin(PERSONAL_EMAIL_DOMAINS)
    is_disposable = domain.isin(DISPOSABLE_EMAIL_DOMAINS)
    is_academic = domain.map(
        lambda d: any(d.endswith(p) or p.strip(".") + "." in d for p in ACADEMIC_DOMAIN_PATTERNS)
        if d else False
    )

    df["is_academic_email"] = is_academic
    df["is_disposable_email"] = is_disposable

    email_type = pd.Series("Unknown", index=df.index)
    valid = df["email_valid"] & (domain != "")
    email_type[valid] = "Corporate"
    email_type[valid & is_personal] = "Personal"
    email_type[valid & is_academic] = "Academic"
    email_type[valid & is_disposable] = "Unknown"  # treat disposables as junk
    df["email_type"] = email_type

    return df
