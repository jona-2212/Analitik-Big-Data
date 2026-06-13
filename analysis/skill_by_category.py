import pandas as pd
import re
from collections import Counter

# =========================
# LOAD DATA
# =========================
df = pd.read_csv("cleaning/jobs_cleaned.csv")

# =========================
# DEFINISI SKILL
# =========================
HARD_SKILLS = {
    'excel', 'microsoft', 'office', 'word', 'powerpoint',
    'python', 'java', 'php', 'javascript', 'react', 'sql', 'mysql',
    'database', 'tableau', 'sap', 'erp', 'seo', 'sem', 'digital',
    'accounting', 'finance', 'keuangan', 'teknik', 'komputer',
    'software', 'ui', 'ux', 'design', 'desain', 'pemasaran',
    'cloud', 'aws', 'azure', 'docker', 'git', 'linux',
    'figma', 'photoshop', 'laravel', 'node.js', 'html', 'css',
    'mongodb', 'kubernetes', 'c#', 'c++',
    'sales', 'marketing',
}

SOFT_SKILLS = {
    'komunikasi', 'communication', 'tim', 'team', 'teamwork', 'kolaborasi',
    'teliti', 'detail', 'jujur', 'disiplin', 'gigih', 'kreatif', 'creative',
    'mandiri', 'independent', 'leadership', 'kepemimpinan', 'problem',
    'solving', 'analitis', 'inggris', 'english',
    'interpersonal', 'negotiation', 'negoisasi',
    'presentasi', 'presentation', 'inovatif', 'innovative',
}

ALL_SKILLS = HARD_SKILLS | SOFT_SKILLS

def extract_skills(text):
    """Ekstrak skill dari teks lowongan."""
    if pd.isna(text):
        return []
    text = str(text).lower()
    words = re.findall(r'\b[a-zA-Z0-9+#./]+\b', text)
    found = [w for w in words if w in ALL_SKILLS]
    return list(set(found))  # unique per lowongan

def classify_skill(skill):
    """Klasifikasi skill jadi Hard/Soft."""
    if skill in HARD_SKILLS:
        return "Hard Skill"
    elif skill in SOFT_SKILLS:
        return "Soft Skill"
    return "Other"

# =========================
# EKSTRAK SKILL PER LOWONGAN
# =========================

df["skills_list"] = df["job_requirements"].apply(extract_skills)

# Explode: 1 baris per skill per lowongan
exploded = df.explode("skills_list").dropna(subset=["skills_list"])
exploded = exploded.rename(columns={"skills_list": "skill"})
exploded["skill_type"] = exploded["skill"].apply(classify_skill)

# ===========================================
# ANALISIS 1: Skill vs Experience Level
# ===========================================
print("=" * 60)
print("ANALISIS 1: TOP SKILLS PER EXPERIENCE GROUP")
print("=" * 60)

for group in ["Fresh Graduate", "Junior", "Mid", "Senior"]:
    subset = exploded[exploded["experience_group"] == group]
    if len(subset) == 0:
        continue
    top = subset["skill"].value_counts().head(10)
    print(f"\n--- {group} ---")
    print(top.to_string())

# Pivot table: skill x experience_group
skill_exp = (
    exploded.groupby(["skill", "experience_group"])
    .size()
    .reset_index(name="count")
    .pivot_table(index="skill", columns="experience_group", values="count", fill_value=0)
)
skill_exp["total"] = skill_exp.sum(axis=1)
skill_exp = skill_exp.sort_values("total", ascending=False)
skill_exp.to_csv("analysis/skill_vs_experience.csv")
print("\n>> Saved: analysis/skill_vs_experience.csv")

# ===========================================
# ANALISIS 2: Skill vs Education Level
# ===========================================
print("\n" + "=" * 60)
print("ANALISIS 2: TOP SKILLS PER EDUCATION LEVEL")
print("=" * 60)

for edu in ["SMA/SMK", "D3", "S1", "S2"]:
    subset = exploded[exploded["education_min"] == edu]
    if len(subset) == 0:
        continue
    top = subset["skill"].value_counts().head(10)
    print(f"\n--- {edu} ---")
    print(top.to_string())

# Pivot table: skill x education_min
skill_edu = (
    exploded.groupby(["skill", "education_min"])
    .size()
    .reset_index(name="count")
    .pivot_table(index="skill", columns="education_min", values="count", fill_value=0)
)
skill_edu["total"] = skill_edu.sum(axis=1)
skill_edu = skill_edu.sort_values("total", ascending=False)
skill_edu.to_csv("analysis/skill_vs_education.csv")
print("\n>> Saved: analysis/skill_vs_education.csv")

# ===========================================
# ANALISIS 3: Hard vs Soft Skill Ratio per Experience
# ===========================================
print("\n" + "=" * 60)
print("ANALISIS 3: RASIO HARD vs SOFT SKILL PER EXPERIENCE")
print("=" * 60)

ratio = (
    exploded.groupby(["experience_group", "skill_type"])
    .size()
    .reset_index(name="count")
    .pivot_table(index="experience_group", columns="skill_type", values="count", fill_value=0)
)
if "Hard Skill" in ratio.columns and "Soft Skill" in ratio.columns:
    ratio["total"] = ratio["Hard Skill"] + ratio["Soft Skill"]
    ratio["hard_pct"] = (ratio["Hard Skill"] / ratio["total"] * 100).round(1)
    ratio["soft_pct"] = (ratio["Soft Skill"] / ratio["total"] * 100).round(1)
ratio.to_csv("analysis/hardsoft_ratio_by_experience.csv")
print(ratio.to_string())
print("\n>> Saved: analysis/hardsoft_ratio_by_experience.csv")

print("\n✅ Analisis skill_by_category selesai!")
