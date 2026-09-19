"""
M4 dataset, part 1 — Career-Skill Semantic Matcher: career profiles table.

Source: O*NET 31.0 (U.S. Dept. of Labor, free/public, CC-BY 4.0 — no signup,
no scraping-policy concerns). Downloaded from onetcenter.org/database.html.

O*NET's newer CSV release renamed the classic "Skills.txt" to
essential_skills.csv, but the shape docs/phases/MENTORA_Phase3_Datasets.md §3.2
assumes is unchanged: one row per (occupation, skill element), with a
Scale ID of "IM" (Importance, 1-5) or "LV" (Level) — we keep IM >= 3.5 to
mean "this skill actually matters for this job."

Scope: SOC major group 15 (Computer and Mathematical Occupations) covers the
core CS/data-track roles directly, plus a curated supplement of business/
management occupations so Business-Analyst- and Product-Manager-style roles
are represented too (the platform's `career_goal` dropdown — data_scientist,
ml_engineer, business_analyst, software_engineer, product_manager — is a
separate, smaller curated list for what a *student* selects as their target;
O*NET doesn't have an exact 1:1 title for each of those 5, and reconciling
that mapping is Phase 6 ranking-logic work, not a dataset concern here).

Run: ~/.venvs/mentora-data/bin/python datasets/m4_career_matcher/build_career_profiles.py
Output: mentora_data/processed/m4/career_profiles.csv
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "raw" / "onet"
OUT_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Curated supplement beyond SOC group 15 — business/management roles relevant
# to a CS/business-track student audience (per docs/phases/MENTORA_Phase3_Datasets.md
# §3.3's "Data Scientist, ML Engineer, Business Analyst, Software Engineer,
# Product Manager, and the surrounding ~45 in that same neighborhood").
SUPPLEMENTAL_CODES = [
    "11-1021.00",  # General and Operations Managers
    "11-2011.00",  # Advertising and Promotions Managers
    "11-2021.00",  # Marketing Managers
    "11-3021.00",  # Computer and Information Systems Managers
    "13-1071.00",  # Human Resources Specialists
    "13-1082.00",  # Project Management Specialists (Product Manager proxy)
    "13-1111.00",  # Management Analysts (Business Analyst proxy)
    "13-1151.00",  # Training and Development Specialists
    "13-1161.00",  # Market Research Analysts and Marketing Specialists
    "13-1161.01",  # Search Marketing Strategists
    "13-2011.00",  # Accountants and Auditors
    "13-1199.00",  # Business Operations Specialists, All Other
    "13-2051.00",  # Financial and Investment Analysts
    "11-2032.00",  # Public Relations Managers
    "27-1024.00",  # Graphic Designers (UX-adjacent)
    "27-3031.00",  # Public Relations Specialists
    "11-2022.00",  # Sales Managers
]

occ = pd.read_csv(RAW_DIR / "occupation_data.csv")
skills = pd.read_csv(RAW_DIR / "essential_skills.csv")

in_scope = occ["O*NET-SOC Code"].str.startswith("15-") | occ["O*NET-SOC Code"].isin(SUPPLEMENTAL_CODES)
occ_scoped = occ[in_scope]

skills_relevant = skills[(skills["Scale ID"] == "IM") & (skills["Data Value"] >= 3.5)]

career_skills = (
    skills_relevant[["O*NET-SOC Code", "Element Name"]]
    .merge(occ_scoped[["O*NET-SOC Code", "Title", "Description"]], on="O*NET-SOC Code")
    .groupby(["O*NET-SOC Code", "Title", "Description"])["Element Name"]
    .apply(lambda names: sorted(set(names)))
    .reset_index()
    .rename(columns={"Element Name": "required_skills", "Title": "title", "Description": "description"})
)
career_skills.insert(0, "career_id", range(1, len(career_skills) + 1))
career_skills = career_skills.rename(columns={"O*NET-SOC Code": "onet_soc_code"})

# Validation checklist (docs/phases/MENTORA_Phase3_Datasets.md §3.4)
assert 50 <= len(career_skills) <= 80, f"Expected 50-80 careers, got {len(career_skills)} — adjust scope"
assert career_skills["required_skills"].map(len).min() > 0, "Every career must have at least one required skill"

career_skills.to_csv(OUT_DIR / "career_profiles.csv", index=False)
print(f"Built {len(career_skills)} career profiles -> {OUT_DIR / 'career_profiles.csv'}")
print("\nSample:")
print(career_skills[["career_id", "title", "required_skills"]].head(8).to_string(index=False))
