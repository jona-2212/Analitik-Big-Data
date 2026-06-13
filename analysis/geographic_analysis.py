import pandas as pd
import re

# =========================
# LOAD DATA
# =========================
df = pd.read_csv("cleaning/jobs_cleaned.csv")

# =========================
# PARSING KOTA DARI LOCATION
# =========================
def extract_city(location):
    """Ambil nama kota dari kolom location."""
    if pd.isna(location):
        return "Unknown"
    loc = str(location)
    
    # Mapping kota-kota utama
    city_keywords = {
        "Jakarta Selatan": "Jakarta",
        "Jakarta Pusat": "Jakarta",
        "Jakarta Timur": "Jakarta",
        "Jakarta Barat": "Jakarta",
        "Jakarta Utara": "Jakarta",
        "Jakarta Raya": "Jakarta",
        "DKI Jakarta": "Jakarta",
        "DKI-Jakarta": "Jakarta",
        "Kebayoran": "Jakarta",
        "Menteng": "Jakarta",
        "Kuningan": "Jakarta",
        "Senayan": "Jakarta",
        "Sudirman": "Jakarta",
        "Surabaya": "Surabaya",
        "Bandung": "Bandung",
        "Semarang": "Semarang",
        "Tangerang": "Tangerang",
        "Bekasi": "Bekasi",
        "Denpasar": "Denpasar",
        "Medan": "Medan",
        "Yogyakarta": "Yogyakarta",
        "Malang": "Malang",
        "Makassar": "Makassar",
        "Pekalongan": "Pekalongan",
        "Bogor": "Bogor",
        "Depok": "Depok",
    }
    
    for keyword, city in city_keywords.items():
        if keyword.lower() in loc.lower():
            return city
    
    return "Lainnya"

df["city"] = df["location"].apply(extract_city)

# =========================
# DEFINISI SKILL REGEX
# =========================
SKILL_PATTERNS = {
    "Excel/Office":       r'\bexcel\b|\bmicrosoft\b|\boffice\b',
    "Sales/Marketing":    r'\bsales\b|\bmarketing\b',
    "SQL/Database":       r'\bsql\b|\bmysql\b|\bdatabase\b',
    "Python":             r'\bpython\b',
    "SAP/ERP":            r'\bsap\b|\berp\b',
    "Communication":      r'\bkomunikasi\b|\bcommunication\b',
    "Teamwork":           r'\btim\b|\bteam\b|\bteamwork\b',
    "Design/UI-UX":       r'\bdesign\b|\bdesain\b|\bfigma\b|\bui\b|\bux\b',
    "Accounting":         r'\baccounting\b|\bkeuangan\b|\bfinance\b',
    "Digital Marketing":  r'\bseo\b|\bdigital\b|\bads\b',
    "Leadership":         r'\bleadership\b|\bkepemimpinan\b',
    "English":            r'\binggris\b|\benglish\b',
}

text_col = df["job_requirements"].fillna("").astype(str).str.lower()

for label, pattern in SKILL_PATTERNS.items():
    df[f"has_{label}"] = text_col.str.contains(pattern, regex=True).astype(int)

# =========================
# JUMLAH LOWONGAN PER KOTA
# =========================
print("=" * 60)
print("ANALISIS GEOGRAFIS")
print("=" * 60)

city_counts = df["city"].value_counts()
print("\n--- JUMLAH LOWONGAN PER KOTA ---")
print(city_counts.to_string())
city_counts.to_csv("analysis/jobs_per_city.csv", header=["jumlah_lowongan"])

# =========================
# TOP SKILL PER KOTA
# =========================
print("\n--- TOP SKILLS PER KOTA (Top 3 Kota) ---")

top_cities = city_counts.head(5).index.tolist()
city_skill_data = []

for city in top_cities:
    city_df = df[df["city"] == city]
    print(f"\n🏙️  {city} ({len(city_df)} lowongan)")
    
    skill_counts = {}
    for label in SKILL_PATTERNS.keys():
        count = city_df[f"has_{label}"].sum()
        if count > 0:
            skill_counts[label] = count
    
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    for skill, count in sorted_skills[:8]:
        pct = count / len(city_df) * 100
        print(f"  {skill:<25} {count:>3} lowongan ({pct:.0f}%)")
        city_skill_data.append({
            "city": city,
            "skill": skill,
            "count": count,
            "percentage": round(pct, 1)
        })

# Simpan ke CSV
city_skill_df = pd.DataFrame(city_skill_data)
city_skill_df.to_csv("analysis/skill_by_city.csv", index=False)

# =========================
# RATA-RATA GAJI PER KOTA
# =========================
print("\n--- RATA-RATA GAJI PER KOTA ---")
salary_city = (
    df[df["salary_avg_numeric"].notna()]
    .groupby("city")["salary_avg_numeric"]
    .agg(["mean", "median", "count"])
    .sort_values("mean", ascending=False)
)
salary_city.columns = ["avg_salary", "median_salary", "jumlah"]
salary_city["avg_salary"] = salary_city["avg_salary"].round(0)
salary_city["median_salary"] = salary_city["median_salary"].round(0)

for city, row in salary_city.iterrows():
    if row["jumlah"] >= 3:
        print(f"  {city:<20} Avg: Rp {row['avg_salary']:>10,.0f}  Median: Rp {row['median_salary']:>10,.0f}  ({int(row['jumlah'])} data)")

salary_city.to_csv("analysis/salary_by_city.csv")

print("\n>> Saved: analysis/jobs_per_city.csv")
print(">> Saved: analysis/skill_by_city.csv")
print(">> Saved: analysis/salary_by_city.csv")
print("\n✅ Analisis geografis selesai!")
