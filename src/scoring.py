"""Lead scoring: 0-100, fully vectorized."""
from __future__ import annotations

import pandas as pd

from .config import HIGH_VALUE_THRESHOLD, LOW_VALUE_THRESHOLD, SCORE_BASE, SCORE_WEIGHTS


def score_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Add lead_score (0-100) and lead_tier (High/Medium/Low)."""
    df = df.copy()
    w = SCORE_WEIGHTS
    score = pd.Series(float(SCORE_BASE), index=df.index)

    # positive signals
    score += (df["email_type"] == "Corporate") * w["corporate_email"]
    score += df["company"].notna() * w["company_present"]
    score += df["has_linkedin"] * w["linkedin_present"]
    score += (df["contact_type"] == "Founder") * w["title_founder"]
    score += (df["contact_type"] == "C-Level") * w["title_c_level"]
    score += (df["contact_type"] == "VP / Director") * w["title_vp_director"]
    score += (df["contact_type"] == "Manager") * w["title_manager"]
    score += df["mobile_valid"] * w["valid_mobile"]
    score += df["country"].notna() * w["country_known"]

    # negative signals
    score += df["student_flag"] * w["student"]
    score += (df["email_type"] == "Personal") * w["personal_email"]
    score += (~df["email_valid"]) * w["invalid_email"]
    score += df["company"].isna() * w["missing_company"]
    score += df["designation"].isna() * w["missing_designation"]
    score += df["suspicious_flag"] * w["suspicious"]

    # incomplete-profile penalty scales with how much of the profile is empty
    score -= (1 - df["completeness"]) * 10

    df["lead_score"] = score.clip(0, 100).round(0).astype(int)
    df["lead_tier"] = pd.cut(
        df["lead_score"],
        bins=[-1, LOW_VALUE_THRESHOLD, HIGH_VALUE_THRESHOLD - 1, 100],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    return df
