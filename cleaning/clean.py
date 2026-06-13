import os
import re
import pandas as pd
from pathlib import Path

# =========================
# 1. LOAD DATA
# =========================
try:
    glints = pd.read_csv("../scrapping/glints_jobs.csv")
    linkedin = pd.read_csv("../scrapping/linkedin_lengkap1.csv")
    karir = pd.read_csv("../scrapping/karir_jobs.csv")
    df = pd.concat([glints, linkedin, karir], ignore_index=True)
except Exception as e:
    # Fallback jika file scrapping tidak ditemukan (menggunakan file yang sudah ada)
    print("Membaca dari jobs_cleaned.csv...")
    df = pd.read_csv("jobs_cleaned.csv")

print("Sebelum cleaning:", df.shape)

# =========================
# 2. HAPUS DUPLIKAT & TRIM SPASI
# =========================
df = df.drop_duplicates()

for col in df.select_dtypes(include="object").columns:
    df[col] = df[col].astype(str).str.strip()
    
# Ubah nilai 'nan' (string) menjadi pd.NA sesungguhnya
df = df.replace(["", "nan", "NaN", "None"], pd.NA)

# =========================
# 3. STANDARDISASI JOB TYPE
# =========================
job_type_mapping = {
    "FULL_TIME": "Full Time",
    "Full Time": "Full Time",
    "CONTRACTOR": "Contract",
    "Contract": "Contract",
    "INTERN": "Internship",
    "Internship": "Internship",
    "Tidak Disebutkan": "Tidak Disebutkan"
}
df["job_type"] = df["job_type"].replace(job_type_mapping)

# =========================
# 4. STANDARDISASI EDUCATION (Ambil Syarat Minimal)
# =========================
def clean_education(edu_str):
    if pd.isna(edu_str): return "Unknown"
    edu_str = str(edu_str).upper()
    
    # Ambil syarat pendidikan paling minim jika ada banyak pilihan
    if "APA SAJA" in edu_str or "ANY" in edu_str: return "Apa Saja"
    if "SD" in edu_str or "PRIMARY" in edu_str: return "SD"
    if "SMA" in edu_str or "SMK" in edu_str or "HIGH SCHOOL" in edu_str: return "SMA/SMK"
    if "D3" in edu_str or "DIPLOMA" in edu_str: return "D3"
    if "S1" in edu_str or "BACHELOR" in edu_str: return "S1"
    if "S2" in edu_str or "MASTER" in edu_str: return "S2"
    
    return "Unknown"

df["education_min"] = df["education_req"].apply(clean_education)

# =========================
# 5. PARSING SALARY (Mengubah teks "Rp 5jt - 6jt" jadi angka)
# =========================
def parse_average_salary(salary_str):
    if pd.isna(salary_str) or salary_str == "Tidak Disebutkan":
        return pd.NA
    
    # Hapus titik (separator ribuan)
    clean_str = str(salary_str).replace(".", "").replace(",", "")
    # Ambil semua angka di dalam teks
    numbers = re.findall(r'\d+', clean_str)
    
    if len(numbers) >= 2:
        # Jika ada range (Misal: 5000000 - 6000000), ambil rata-ratanya
        return (float(numbers[0]) + float(numbers[1])) / 2
    elif len(numbers) == 1:
        # Jika cuma 1 angka
        return float(numbers[0])
    return pd.NA

df["salary_avg_numeric"] = df["salary_range"].apply(parse_average_salary)

# =========================
# 6. EXPERIENCE GROUP & TAHUN MINIMAL
# =========================
def get_experience_group(exp):
    if pd.isna(exp) or exp == "Unknown": return "Unknown"
    exp = str(exp).lower()
    
    if "0" in exp or "fresh" in exp: return "Fresh Graduate"
    elif "1" in exp or "2" in exp: return "Junior"
    elif "3" in exp or "4" in exp or "5" in exp: return "Mid"
    elif "8" in exp or "10" in exp or "18" in exp or "20" in exp: return "Senior"
    
    return "Unknown"

df["experience_group"] = df["experience_level"].apply(get_experience_group)

# =========================
# 7. FEATURE ENGINEERING (Ekstraksi Skill 1/0)
# =========================
# Menggabungkan requirements & responsibilities untuk pencarian skill
df["all_text"] = df["job_requirements"].fillna("") + " " + df["job_responsibilities"].fillna("")
df["all_text"] = df["all_text"].str.lower().str.replace('tanggung jawab', 'tanggungjawab')

# Menambahkan kolom boolean (1 atau 0) untuk skill top
skills_to_extract = {
    "req_sales": r'\bsales\b|\bmarketing\b',
    "req_excel_office": r'\bexcel\b|\bmicrosoft\b|\boffice\b',
    "req_komunikasi": r'\bkomunikasi\b|\bcommunication\b',
    "req_english": r'\binggris\b|\benglish\b'
}

for col_name, pattern in skills_to_extract.items():
    # Jika ketemu regex-nya, isi 1, jika tidak isi 0
    df[col_name] = df["all_text"].apply(lambda x: 1 if re.search(pattern, str(x)) else 0)

# Hapus kolom bantuan
df = df.drop(columns=["all_text"])

# =========================
# 8. CEK & SIMPAN DATA
# =========================
print("\n--- INFO DATASET SETELAH CLEANING ---")
print("Missing Values Baru:")
print(df[["salary_avg_numeric", "education_min"]].isnull().sum())

print("\nDistribusi Minimum Education:")
print(df["education_min"].value_counts())

OUTPUT_FILE = "jobs_cleaned.csv"
df.to_csv(OUTPUT_FILE, index=False)

print(f"\nSaved to: {OUTPUT_FILE}")
print("Setelah cleaning:", df.shape)