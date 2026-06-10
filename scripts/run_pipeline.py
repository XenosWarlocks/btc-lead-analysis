"""CLI: process every CSV/Excel in data/raw and write data/processed/leads.parquet.

Usage:
    python scripts/run_pipeline.py [raw_dir]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import pipeline  # noqa: E402

raw_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
df = pipeline.run_on_directory(raw_dir)
if df.empty:
    print(f"No CSV/Excel files found in {raw_dir.resolve()}")
    sys.exit(1)

out = pipeline.save_processed(df)
print(f"Processed {len(df):,} unique leads -> {out}")
print("\nContact types:")
print(df["contact_type"].value_counts().to_string())
print("\nEmail types:")
print(df["email_type"].value_counts().to_string())
print(f"\nStudents flagged: {int(df['student_flag'].sum())}")
print(f"Suspicious records: {int(df['suspicious_flag'].sum())}")
print(f"Mean lead score: {df['lead_score'].mean():.1f}")
print(f"High-value leads (>=80): {int((df['lead_score'] >= 80).sum())}")
