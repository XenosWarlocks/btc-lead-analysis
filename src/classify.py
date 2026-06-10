"""Contact classification and student detection.

Strategy (in order of trust):
 1. Rule tier  - word-boundary keyword matching on the normalized title.
 2. Fuzzy tier - RapidFuzz token_set_ratio against canonical titles, which
                 catches typos ("Maneger", "Studnet", "Founedr").
 3. Context    - academic email domain / university company name reinforce
                 or trigger the student flag.

Classification is computed once per UNIQUE normalized title and then mapped
back, so 100k rows with ~3k unique titles cost ~3k classifications.
"""
from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz, process

from .config import (
    C_LEVEL_PATTERNS,
    EDU_COMPANY_PATTERNS,
    EMPLOYEE_PATTERNS,
    FOUNDER_PATTERNS,
    FUZZY_CANONICAL_TITLES,
    FUZZY_MATCH_THRESHOLD,
    MANAGER_PATTERNS,
    STUDENT_PATTERNS,
    VP_DIRECTOR_PATTERNS,
)

CONTACT_TYPES = ["Founder", "C-Level", "VP / Director", "Manager",
                 "Employee", "Student", "Unknown"]


def _compile(patterns) -> re.Pattern:
    """One regex matching any pattern as whole words."""
    alts = sorted((re.escape(p) for p in patterns), key=len, reverse=True)
    return re.compile(r"(?<![\w])(?:" + "|".join(alts) + r")(?![\w])")

_RULES = [
    # (label, regex, rule confidence)
    ("Student", _compile(STUDENT_PATTERNS), 0.95),
    ("Founder", _compile(FOUNDER_PATTERNS), 0.95),
    ("C-Level", _compile(C_LEVEL_PATTERNS), 0.95),
    ("VP / Director", _compile(VP_DIRECTOR_PATTERNS), 0.9),
    ("Manager", _compile(MANAGER_PATTERNS), 0.85),
    ("Employee", _compile(EMPLOYEE_PATTERNS), 0.8),
]
_RULE_BY_LABEL = {label: rx for label, rx, _ in _RULES}

# Seniority precedence when several rules fire on one title:
# "Founder & CEO" -> Founder; "Engineering Manager Intern" -> Student.
_PRECEDENCE = ["Founder", "C-Level", "Student", "VP / Director",
               "Manager", "Employee"]

_FUZZY_CHOICES = list(FUZZY_CANONICAL_TITLES.keys())

_EDU_COMPANY_RE = _compile([p.strip() for p in EDU_COMPANY_PATTERNS])


@lru_cache(maxsize=100_000)
def classify_title(title_norm: str) -> tuple[str, float]:
    """Classify one normalized title. Returns (contact_type, confidence)."""
    if not title_norm:
        return "Unknown", 0.0

    hits = {label: bool(rx.search(title_norm)) for label, rx, _ in _RULES}

    # "Vice President" must not count as C-Level just because it contains
    # "president": drop C-Level hits whose every match sits inside a longer
    # VP-tier phrase ("managing director" survives - "director" is the
    # contained one there, not the C-Level match).
    if hits["C-Level"] and hits["VP / Director"]:
        vp_spans = [m.span() for m in _RULE_BY_LABEL["VP / Director"].finditer(title_norm)]
        c_spans = [m.span() for m in _RULE_BY_LABEL["C-Level"].finditer(title_norm)]
        hits["C-Level"] = any(
            not any(v0 <= c0 and c1 <= v1 and (v0, v1) != (c0, c1)
                    for v0, v1 in vp_spans)
            for c0, c1 in c_spans
        )

    matched = [label for label in _PRECEDENCE if hits[label]]

    if matched:
        label = matched[0]
        # Student keywords lose to an explicit senior title UNLESS the
        # student signal is the dominant one ("intern" as the head noun).
        if label == "Student" and (hits["Founder"] or hits["C-Level"]):
            label = "Founder" if hits["Founder"] else "C-Level"
        conf = dict((l, c) for l, _, c in _RULES)[label]
        return label, conf

    # Fuzzy fallback for typos and unseen phrasings.
    best = process.extractOne(
        title_norm, _FUZZY_CHOICES, scorer=fuzz.token_set_ratio,
        score_cutoff=FUZZY_MATCH_THRESHOLD,
    )
    if best:
        choice, score, _ = best
        return FUZZY_CANONICAL_TITLES[choice], round(score / 100 * 0.75, 2)

    return "Unknown", 0.0


def is_edu_company(company_norm: str) -> bool:
    return bool(company_norm) and bool(_EDU_COMPANY_RE.search(company_norm))


def classify_contacts(df: pd.DataFrame) -> pd.DataFrame:
    """Add contact_type, student_flag, confidence_score, is_edu_company."""
    df = df.copy()

    unique_titles = df["designation_norm"].fillna("").unique()
    title_map = {t: classify_title(t) for t in unique_titles}
    results = df["designation_norm"].fillna("").map(title_map)
    df["contact_type"] = results.map(lambda r: r[0])
    df["confidence_score"] = results.map(lambda r: r[1])

    unique_companies = df["company_norm"].fillna("").unique()
    edu_map = {c: is_edu_company(c) for c in unique_companies}
    df["is_edu_company"] = df["company_norm"].fillna("").map(edu_map)

    # ----- student detection beyond the title rules ---------------------
    title_student = df["contact_type"] == "Student"
    edu_signal = df["is_edu_company"] | df.get(
        "is_academic_email", pd.Series(False, index=df.index)
    )
    # University/college in the company field with no senior title is a
    # strong student signal even when the title says nothing.
    weak_title = df["contact_type"].isin(["Unknown", "Employee"])
    inferred_student = edu_signal & weak_title & ~title_student

    df["student_flag"] = title_student | inferred_student

    # Confidence: title-based keeps its rule confidence (boosted by edu
    # context); inferred students get a moderate score.
    conf = df["confidence_score"].copy()
    conf[title_student & edu_signal] = conf[title_student & edu_signal].clip(lower=0.99)
    conf[inferred_student] = conf[inferred_student].clip(lower=0.65)
    df.loc[inferred_student, "contact_type"] = "Student"
    df["confidence_score"] = conf.round(2)

    return df
