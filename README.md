# Lead Intelligence Dashboard

A Python system that cleans, classifies, enriches, scores, and visualizes
20k–100k+ B2B leads, with a real-time Streamlit dashboard that prioritizes
company contacts and filters out students and junk records.

## Quick start

```bash
pip install -r requirements.txt

# Option A: drop your CSV/Excel exports into data/raw/, then
streamlit run app.py

# Option B (batch): precompute data/processed/leads.parquet
python scripts/run_pipeline.py
```

You can also upload files directly in the dashboard sidebar; uploads are
merged and deduplicated with everything already in `data/raw/`.

---

## 1. System architecture

```
                ┌──────────────────────────────────────────────┐
 CSV / Excel ──▶│                INGESTION (src/ingest.py)      │
 (data/raw/,    │  encoding fallback · bad-line skip · header   │
  uploads)      │  alias mapping · merge · dedupe (best record) │
                └───────────────────┬──────────────────────────┘
                                    ▼
                ┌──────────────────────────────────────────────┐
                │             CLEANING (src/cleaning.py)        │
                │  placeholder nulling · company/title/country  │
                │  normalization · email & mobile validation ·  │
                │  suspicious-record flag                       │
                └───────────────────┬──────────────────────────┘
                                    ▼
                ┌──────────────────────────────────────────────┐
                │   ENRICHMENT (email_intel.py · classify.py)   │
                │  email_type/domain · contact_type (rules +    │
                │  RapidFuzz) · student_flag + confidence       │
                └───────────────────┬──────────────────────────┘
                                    ▼
                ┌──────────────────────────────────────────────┐
                │            SCORING (src/scoring.py)           │
                │  vectorized 0–100 lead_score · lead_tier      │
                └───────────────────┬──────────────────────────┘
                                    ▼
            data/processed/leads.parquet  (cached snapshot)
                                    ▼
                ┌──────────────────────────────────────────────┐
                │        DASHBOARD (app.py + src/filters.py)    │
                │  st.cache_data · boolean-mask filter engine · │
                │  Plotly charts · CSV/Excel export             │
                └──────────────────────────────────────────────┘
```

Everything is a pure `DataFrame -> DataFrame` stage, so stages are testable
in isolation and the same pipeline runs from the CLI and the dashboard.

## 2. Schema

**Raw input** (any subset, any header spelling — aliases are mapped):
`user_id, username, email, dob, interest, interests, country_code, mobile,
country, city, designation, company, pincode, ran, linkedin, instagram, twitter`

**Enriched output** (one row per unique lead):

| Column | Type | Description |
|---|---|---|
| `email_domain` | str | domain part of the email |
| `email_type` | enum | Corporate / Personal / Academic / Unknown |
| `email_valid` | bool | regex-valid email |
| `designation_norm` | str | lowercased, abbreviations expanded (sr → senior) |
| `contact_type` | enum | Founder / C-Level / VP / Director / Manager / Employee / Student / Unknown |
| `student_flag` | bool | student detected (title, edu email, or edu company) |
| `confidence_score` | 0–1 | classification confidence |
| `company_norm` | str | match key, legal suffixes stripped |
| `is_edu_company` | bool | company is a university/college/institute |
| `country` | str | canonical name; derived from phone `country_code` when blank |
| `mobile_valid` | bool | 7–15 digits, not a single repeated digit |
| `has_linkedin` | bool | LinkedIn URL present |
| `suspicious_flag` | bool | ≥2 junk signals (invalid email+phone, gibberish name, shifted columns…) |
| `completeness` | 0–1 | share of 8 key fields filled |
| `lead_score` | 0–100 | see scoring logic |
| `lead_tier` | enum | High (≥80) / Medium / Low (≤40) |
| `source_file` | str | provenance for multi-file imports |

Storage is Parquet (columnar, typed, ~10× faster load than CSV). No DB is
needed at this scale; if the dataset outgrows memory, the same schema maps
1:1 onto SQLite/DuckDB.

## 3. Folder structure

```
btc-lead-analysis/
├── app.py                  # Streamlit dashboard
├── requirements.txt
├── data/
│   ├── raw/                # drop source CSV/Excel here
│   └── processed/          # leads.parquet snapshot
├── scripts/
│   └── run_pipeline.py     # batch CLI
└── src/
    ├── config.py           # domain lists, title taxonomy, weights
    ├── ingest.py           # load / merge / dedupe
    ├── cleaning.py         # normalization + validity flags
    ├── email_intel.py      # email typing
    ├── classify.py         # contact + student classification
    ├── scoring.py          # lead score
    ├── filters.py          # dashboard filter engine
    └── pipeline.py         # orchestrator
```

## 4. Classification strategy

Three tiers, cheapest first; each unique title is classified once and cached
(`lru_cache`), then mapped onto all rows:

1. **Rule tier** — word-boundary regex per category (Founder, C-Level,
   VP/Director, Manager, Student, Employee). Seniority precedence resolves
   multi-hit titles: *Founder & CEO → Founder*, *Engineering Manager Intern →
   Student*. Span containment prevents *Vice President* matching C-Level via
   "president" while keeping *Managing Director* C-Level.
2. **Fuzzy tier (RapidFuzz)** — `token_set_ratio ≥ 85` against canonical
   titles catches typos: *Maneger → Manager*, *Studnet → Student*.
3. **Context tier (student detection)** — even with no student keyword, a
   lead is flagged when the email domain is academic (`.edu`, `.ac.in`, …) or
   the company is a university/institute/college and no senior title is
   present. Output: `student_flag` + `confidence_score`.

**Optional LLM tier**: titles still `Unknown` with non-empty designation are
a small set (typically <2 % of rows); batch them to the Claude API for
classification and persist results to a lookup file so each title is paid
for once.

## 5. Lead scoring logic

`score = 30 (base) + Σ weights`, clipped to 0–100 (`src/config.py`):

| Signal | Weight | | Signal | Weight |
|---|---|---|---|---|
| Founder title | +20 | | Student | −35 |
| C-Level title | +18 | | Invalid email | −20 |
| Corporate email | +15 | | Missing company | −15 |
| VP/Director title | +12 | | Missing designation | −10 |
| Company present | +10 | | Suspicious record | −10 |
| LinkedIn present | +10 | | Personal email | −8 |
| Manager title | +6 | | Incomplete profile | up to −10 |
| Valid mobile | +3 | | | |
| Country known | +2 | | | |

A founder with corporate email, company, and LinkedIn lands ≈ 90+; a student
on Gmail with no company lands ≈ 0. Tiers: **High ≥ 80**, Low ≤ 40.

## 6–7. Dashboard & filtering engine

- **Sidebar**: multi-file upload, quick presets ("Founders with corporate
  email", "Exclude students", "Score ≥ 80"…), global search, and every
  filter from the spec (email type, contact type, country, city, company,
  score range, LinkedIn yes/no, students include/exclude/only, valid-email,
  hide-suspicious). All filters compose (AND).
- **Global search** runs over a precomputed lowercase `_search` blob
  (name+company+email+title) — one `str.contains` per term.
- **Filter engine** (`src/filters.py`) builds a single boolean mask;
  filtering 100k rows takes milliseconds, so every widget change re-renders
  table + charts instantly without page refresh.
- **Tabs**: 📋 Leads (sortable table, score progress bars, CSV/Excel export
  of the current filter), 📊 Analytics (country, contact-type donut,
  corporate-vs-personal, top domains, score histogram, top companies,
  designations, cities — all filter-reactive), 🧹 Data Quality (invalid
  emails, completeness per field, suspicious records).

## 8. Performance (20k–100k records)

- **Pandas is sufficient**: the whole enriched table at 100k rows is
  ~100 MB; the full pipeline runs in seconds. Polars/DuckDB only become
  worth it past ~1M rows.
- **Classify unique values, not rows**: titles and companies are classified
  once per unique value (20k rows ≈ 2–4k unique titles) and mapped back.
- **Vectorized everything else**: scoring, email typing, flags are pure
  column ops — no `df.apply` row loops.
- **`st.cache_data` keyed on file content**: the pipeline reruns only when
  input files change; filter interactions hit only the boolean-mask path.
- **Parquet snapshot** for batch mode; precomputed `_search` blob for
  search.

## 9. Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1. MVP | ingestion, cleaning, email intel, rules+fuzzy classification, scoring, dashboard, export | ✅ done (this repo) |
| 2. Quality | unit tests per stage, country/title dictionaries expansion, fuzzy company dedupe (RapidFuzz on `company_norm`) | next |
| 3. Enrichment | MX-record email verification, LLM classification for `Unknown` titles, LinkedIn URL validation | later |
| 4. Scale | DuckDB/Polars backend, FastAPI + React if multi-user, scheduled re-ingestion | if needed |

## 10. Sample usage

```python
from src import pipeline

df = pipeline.run_on_directory("data/raw")      # full enrichment
hot = df[(df.lead_score >= 80) & ~df.student_flag]
hot.to_csv("hot_leads.csv", index=False)
```
