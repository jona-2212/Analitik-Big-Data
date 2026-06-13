import pandas as pd
import re

# =========================
# LOAD DATA
# =========================
df = pd.read_csv("cleaning/jobs_cleaned.csv")

# =========================
# DEFINISI SKILL UNTUK PENCOCOKAN
# =========================
# Setiap entry: (nama_kolom, regex_pattern, label_skill)
SKILL_PATTERNS = [
    ("has_excel",       r'\bexcel\b|\bmicrosoft\b|\boffice\b', "Excel/Office"),
    ("has_sql",         r'\bsql\b|\bmysql\b|\bdatabase\b',     "SQL/Database"),
    ("has_python",      r'\bpython\b',                          "Python"),
    ("has_java",        r'\bjava\b',                            "Java"),
    ("has_sap",         r'\bsap\b|\berp\b',                     "SAP/ERP"),
    ("has_sales",       r'\bsales\b|\bmarketing\b',             "Sales/Marketing"),
    ("has_accounting",  r'\baccounting\b|\bkeuangan\b|\bfinance\b', "Accounting/Finance"),
    ("has_design",      r'\bdesign\b|\bdesain\b|\bfigma\b|\bui\b|\bux\b', "Design/UI-UX"),
    ("has_cloud",       r'\baws\b|\bazure\b|\bcloud\b',         "Cloud (AWS/Azure)"),
    ("has_digital",     r'\bseo\b|\bdigital\b|\bads\b',         "Digital Marketing"),
    ("has_leadership",  r'\bleadership\b|\bkepemimpinan\b',     "Leadership"),
    ("has_communication", r'\bkomunikasi\b|\bcommunication\b',  "Communication"),
    ("has_english",     r'\binggris\b|\benglish\b',             "English Proficiency"),
    ("has_teamwork",    r'\btim\b|\bteam\b|\bteamwork\b',       "Teamwork"),
]

# Gabungkan teks requirements untuk matching
text_col = df["job_requirements"].fillna("").astype(str).str.lower()

# Buat kolom boolean untuk setiap skill
for col_name, pattern, label in SKILL_PATTERNS:
    df[col_name] = text_col.str.contains(pattern, regex=True).astype(int)

# =========================
# FILTER HANYA YANG ADA SALARY
# =========================
salary_df = df[df["salary_avg_numeric"].notna()].copy()

print("=" * 60)
print("ANALISIS SALARY vs SKILL")
print(f"Data dengan salary: {len(salary_df)} dari {len(df)} lowongan")
print("=" * 60)

# =========================
# RATA-RATA GAJI PER SKILL
# =========================
print("\n--- RATA-RATA GAJI BERDASARKAN SKILL ---")
print(f"{'Skill':<25} {'Punya Skill':>12} {'Tidak Punya':>12} {'Selisih':>12}")
print("-" * 65)

salary_results = []
for col_name, pattern, label in SKILL_PATTERNS:
    has_skill = salary_df[salary_df[col_name] == 1]["salary_avg_numeric"]
    no_skill = salary_df[salary_df[col_name] == 0]["salary_avg_numeric"]
    
    if len(has_skill) >= 3:  # minimal 3 data biar valid
        avg_has = has_skill.mean()
        avg_no = no_skill.mean()
        selisih = avg_has - avg_no
        
        salary_results.append({
            "skill": label,
            "avg_salary_with": round(avg_has),
            "avg_salary_without": round(avg_no),
            "salary_diff": round(selisih),
            "count_with": len(has_skill),
            "count_without": len(no_skill),
        })
        
        sign = "+" if selisih > 0 else ""
        print(f"{label:<25} Rp {avg_has:>10,.0f} Rp {avg_no:>10,.0f} {sign}Rp {selisih:>8,.0f}")

salary_result_df = pd.DataFrame(salary_results)
salary_result_df = salary_result_df.sort_values("salary_diff", ascending=False)
salary_result_df.to_csv("analysis/salary_vs_skill.csv", index=False)

# =========================
# RATA-RATA GAJI PER EXPERIENCE GROUP
# =========================
print("\n--- RATA-RATA GAJI PER EXPERIENCE GROUP ---")
salary_by_exp = (
    salary_df.groupby("experience_group")["salary_avg_numeric"]
    .agg(["mean", "median", "count"])
    .sort_values("mean", ascending=False)
)
salary_by_exp.columns = ["avg_salary", "median_salary", "jumlah"]
salary_by_exp["avg_salary"] = salary_by_exp["avg_salary"].round(0)
salary_by_exp["median_salary"] = salary_by_exp["median_salary"].round(0)
print(salary_by_exp.to_string())
salary_by_exp.to_csv("analysis/salary_by_experience.csv")

# =========================
# RATA-RATA GAJI PER EDUCATION
# =========================
print("\n--- RATA-RATA GAJI PER EDUCATION ---")
salary_by_edu = (
    salary_df.groupby("education_min")["salary_avg_numeric"]
    .agg(["mean", "median", "count"])
    .sort_values("mean", ascending=False)
)
salary_by_edu.columns = ["avg_salary", "median_salary", "jumlah"]
salary_by_edu["avg_salary"] = salary_by_edu["avg_salary"].round(0)
salary_by_edu["median_salary"] = salary_by_edu["median_salary"].round(0)
print(salary_by_edu.to_string())
salary_by_edu.to_csv("analysis/salary_by_education.csv")

# =========================
# TOP 10 SKILL YANG BAYAR PALING TINGGI
# =========================
print("\n--- TOP 10 SKILL DENGAN GAJI TERTINGGI ---")
top_salary = salary_result_df.head(10)
for _, row in top_salary.iterrows():
    print(f"  {row['skill']:<25} Rp {row['avg_salary_with']:>10,.0f}  ({row['count_with']} lowongan)")

print("\n>> Saved: analysis/salary_vs_skill.csv")
print(">> Saved: analysis/salary_by_experience.csv")
print(">> Saved: analysis/salary_by_education.csv")
print("\n✅ Analisis salary selesai!")
