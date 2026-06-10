"""Lead Intelligence Dashboard (Streamlit).

Run:  streamlit run app.py
Data: drop CSV/Excel exports in data/raw/ or upload via the sidebar.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src import ingest, pipeline
from src.config import HIGH_VALUE_THRESHOLD
from src.filters import LeadFilters, apply_filters

st.set_page_config(page_title="Lead Intelligence Dashboard", page_icon="🎯",
                   layout="wide")

RAW_DIR = Path(__file__).parent / "data" / "raw"

DISPLAY_COLUMNS = [
    "username", "email", "email_type", "designation", "contact_type",
    "company", "country", "city", "mobile", "linkedin", "lead_score",
    "lead_tier", "student_flag", "confidence_score", "suspicious_flag",
    "source_file",
]

PRESETS = {
    "— none —": {},
    "CEOs / C-Level only": {"contact_types": ["C-Level"]},
    "Founders with corporate email": {"contact_types": ["Founder"],
                                      "email_types": ["Corporate"]},
    "Exclude students": {"students": "Exclude"},
    "High-value leads (score ≥ 80)": {"score_range": (80, 100)},
    "Decision makers (Founder/C-Level/VP-Dir)": {
        "contact_types": ["Founder", "C-Level", "VP / Director"],
        "students": "Exclude"},
    "Corporate emails only": {"email_types": ["Corporate"]},
}


# ---------------------------------------------------------------------------
# Data loading (cached on file content, so re-runs are instant)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Processing leads…")
def process_uploads(file_payloads: tuple) -> pd.DataFrame:
    frames = [ingest.load_file(io.BytesIO(data), name=name)
              for name, data in file_payloads]
    return pipeline.run(pd.concat(frames, ignore_index=True))


@st.cache_data(show_spinner="Processing leads…")
def process_raw_dir(_mtimes: tuple) -> pd.DataFrame:
    return pipeline.run_on_directory(RAW_DIR)


def load_data(uploads) -> pd.DataFrame:
    payloads = tuple((f.name, f.getvalue()) for f in uploads) if uploads else ()
    raw_files = tuple(sorted(
        (p.name, p.stat().st_mtime) for p in RAW_DIR.glob("*")
        if p.suffix.lower() in (".csv", ".xlsx", ".xls", ".xlsm")
    )) if RAW_DIR.exists() else ()

    frames = []
    if raw_files:
        frames.append(process_raw_dir(raw_files))
    if payloads:
        frames.append(process_uploads(payloads))
    if not frames:
        return pd.DataFrame()
    if len(frames) == 1:
        return frames[0]
    # Files arrived from two sources: merge + dedupe across them again.
    return pipeline.run(pd.concat(frames, ignore_index=True))


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="leads")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Sidebar: data source + filters
# ---------------------------------------------------------------------------
st.sidebar.title("🎯 Lead Intelligence")

uploads = st.sidebar.file_uploader(
    "Import CSV / Excel", type=["csv", "xlsx", "xls", "xlsm"],
    accept_multiple_files=True,
    help="Files are merged and deduplicated with everything in data/raw/.",
)

df = load_data(uploads)
if df.empty:
    st.info("No data yet. Drop CSV/Excel files into **data/raw/** or use the "
            "sidebar uploader.")
    st.stop()

st.sidebar.caption(f"{len(df):,} unique leads loaded")
st.sidebar.divider()

preset_name = st.sidebar.selectbox("Quick preset", list(PRESETS))
preset = PRESETS[preset_name]

search = st.sidebar.text_input(
    "🔍 Global search", placeholder="name, company, email, title…")

email_types = st.sidebar.multiselect(
    "Email type", sorted(df["email_type"].dropna().unique()),
    default=preset.get("email_types", []))
contact_types = st.sidebar.multiselect(
    "Contact type", ["Founder", "C-Level", "VP / Director", "Manager",
                     "Employee", "Student", "Unknown"],
    default=preset.get("contact_types", []))
countries = st.sidebar.multiselect(
    "Country", sorted(df["country"].dropna().unique()))
cities = st.sidebar.multiselect("City", sorted(df["city"].dropna().unique()))
companies = st.sidebar.multiselect(
    "Company", sorted(df["company"].dropna().unique()))

score_range = st.sidebar.slider(
    "Lead score", 0, 100, preset.get("score_range", (0, 100)))
linkedin = st.sidebar.radio("LinkedIn available", ["Any", "Yes", "No"],
                            horizontal=True)
students = st.sidebar.radio(
    "Students", ["Include", "Exclude", "Only"], horizontal=True,
    index=["Include", "Exclude", "Only"].index(preset.get("students", "Include")))
valid_email_only = st.sidebar.checkbox("Valid emails only")
hide_suspicious = st.sidebar.checkbox("Hide suspicious records")

flt = LeadFilters(
    search=search, email_types=email_types, contact_types=contact_types,
    countries=countries, cities=cities, companies=companies,
    score_range=score_range, linkedin=linkedin, students=students,
    valid_email_only=valid_email_only, hide_suspicious=hide_suspicious,
)
fdf = apply_filters(df, flt)

# ---------------------------------------------------------------------------
# KPI header
# ---------------------------------------------------------------------------
st.title("Lead Intelligence Dashboard")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Leads (filtered)", f"{len(fdf):,}", f"of {len(df):,}")
k2.metric("Corporate emails",
          f"{(fdf['email_type'] == 'Corporate').mean() * 100:.0f}%"
          if len(fdf) else "—")
k3.metric("High-value (≥80)", f"{(fdf['lead_score'] >= HIGH_VALUE_THRESHOLD).sum():,}")
k4.metric("Decision makers",
          f"{fdf['contact_type'].isin(['Founder', 'C-Level', 'VP / Director']).sum():,}")
k5.metric("Students", f"{fdf['student_flag'].sum():,}")
k6.metric("Avg score", f"{fdf['lead_score'].mean():.0f}" if len(fdf) else "—")

tab_leads, tab_charts, tab_quality = st.tabs(
    ["📋 Leads", "📊 Analytics", "🧹 Data Quality"])

# ---------------------------------------------------------------------------
# Leads table + export
# ---------------------------------------------------------------------------
with tab_leads:
    show_cols = [c for c in DISPLAY_COLUMNS if c in fdf.columns]
    st.dataframe(
        fdf[show_cols].sort_values("lead_score", ascending=False),
        use_container_width=True, height=520, hide_index=True,
        column_config={
            "lead_score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%d"),
            "linkedin": st.column_config.LinkColumn("LinkedIn"),
        },
    )

    export_df = fdf[show_cols].sort_values("lead_score", ascending=False)
    c1, c2, _ = st.columns([1, 1, 4])
    c1.download_button(
        "⬇️ Export CSV", export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="leads_filtered.csv", mime="text/csv",
        use_container_width=True)
    c2.download_button(
        "⬇️ Export Excel", to_excel_bytes(export_df),
        file_name="leads_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True)

# ---------------------------------------------------------------------------
# Analytics (all charts react to the active filters)
# ---------------------------------------------------------------------------
with tab_charts:
    if fdf.empty:
        st.warning("No leads match the current filters.")
    else:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            by_country = (fdf["country"].value_counts().head(15)
                          .rename_axis("country").reset_index(name="leads"))
            st.plotly_chart(px.bar(by_country, x="leads", y="country",
                                   orientation="h", title="Leads by country"),
                            use_container_width=True)
        with r1c2:
            by_type = (fdf["contact_type"].value_counts()
                       .rename_axis("contact_type").reset_index(name="leads"))
            st.plotly_chart(px.pie(by_type, names="contact_type", values="leads",
                                   title="Contact classification", hole=0.45),
                            use_container_width=True)

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            by_email = (fdf["email_type"].value_counts()
                        .rename_axis("email_type").reset_index(name="leads"))
            st.plotly_chart(px.pie(by_email, names="email_type", values="leads",
                                   title="Corporate vs personal email", hole=0.45),
                            use_container_width=True)
        with r2c2:
            domains = (fdf.loc[fdf["email_type"] != "Unknown", "email_domain"]
                       .value_counts().head(15)
                       .rename_axis("domain").reset_index(name="leads"))
            st.plotly_chart(px.bar(domains, x="leads", y="domain",
                                   orientation="h", title="Top email domains"),
                            use_container_width=True)

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            st.plotly_chart(
                px.histogram(fdf, x="lead_score", nbins=20, color="lead_tier",
                             title="Lead score distribution",
                             category_orders={"lead_tier": ["Low", "Medium", "High"]}),
                use_container_width=True)
        with r3c2:
            companies_top = (fdf.loc[fdf["company"].notna(), "company"]
                             .value_counts().head(15)
                             .rename_axis("company").reset_index(name="contacts"))
            st.plotly_chart(px.bar(companies_top, x="contacts", y="company",
                                   orientation="h",
                                   title="Top companies by contacts"),
                            use_container_width=True)

        by_desig = (fdf.loc[fdf["designation"].notna(), "designation"]
                    .str.title().value_counts().head(20)
                    .rename_axis("designation").reset_index(name="leads"))
        st.plotly_chart(px.bar(by_desig, x="designation", y="leads",
                               title="Top designations"),
                        use_container_width=True)

        if fdf["city"].notna().any():
            by_city = (fdf["city"].value_counts().head(15)
                       .rename_axis("city").reset_index(name="leads"))
            st.plotly_chart(px.bar(by_city, x="leads", y="city", orientation="h",
                                   title="Leads by city"),
                            use_container_width=True)

# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------
with tab_quality:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Invalid emails", f"{(~df['email_valid']).sum():,}")
    q2.metric("Missing company", f"{df['company'].isna().sum():,}")
    q3.metric("Missing designation", f"{df['designation'].isna().sum():,}")
    q4.metric("Suspicious records", f"{df['suspicious_flag'].sum():,}")

    st.subheader("Field completeness")
    fields = ["username", "email", "mobile", "country", "city",
              "designation", "company", "linkedin"]
    completeness = pd.DataFrame({
        "field": fields,
        "filled_%": [round(df[f].notna().mean() * 100, 1) for f in fields],
    })
    st.plotly_chart(px.bar(completeness, x="field", y="filled_%",
                           range_y=[0, 100], title="Non-empty values per field"),
                    use_container_width=True)

    st.subheader("Suspicious / low-quality records")
    bad = df[df["suspicious_flag"] | ~df["email_valid"]]
    st.dataframe(bad[[c for c in DISPLAY_COLUMNS if c in bad.columns]],
                 use_container_width=True, height=300, hide_index=True)
