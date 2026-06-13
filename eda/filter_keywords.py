import pandas as pd
from collections import Counter
import re

# ==========================================
# KODE ASLI ANDA
# ==========================================
df = pd.read_csv("cleaning/jobs_cleaned.csv")

all_text = " ".join(
    df["job_requirements"]
    .fillna("")
    .astype(str)
    .str.lower()
)

words = re.findall(r'\b[a-zA-Z0-9+#./]+\b', all_text)
counter = Counter(words)

# ==========================================
# TAMBAHAN UNTUK SORTIR (FILTERING)
# ==========================================

# 1. Definisikan kata apa saja yang mau ditangkap sebagai Hard Skill & Soft Skill
hard_skills_keywords = {
    'sales', 'marketing', 'excel', 'microsoft', 'office', 'word', 'powerpoint',
    'python', 'java', 'php', 'javascript', 'js', 'react', 'sql', 'mysql',
    'database', 'tableau', 'sap', 'erp', 'seo', 'sem', 'digital', 'ads',
    'accounting', 'finance', 'keuangan', 'teknik', 'komputer',
    'software', 'ui', 'ux', 'design', 'desain', 'pemasaran', 'pajak', 'cloud'
}

soft_skills_keywords = {
    'komunikasi', 'communication', 'tim', 'team', 'teamwork', 'kolaborasi',
    'teliti', 'detail', 'jujur', 'disiplin', 'gigih', 'kreatif', 'creative',
    'mandiri', 'independent', 'leadership', 'kepemimpinan', 'problem',
    'solving', 'analitis', 
    'inggris', 'english'
}

# 2. Siapkan list kosong untuk menampung hasil sortir
hard_skills_result = []
soft_skills_result = []

# 3. Looping hasil counter, lalu kelompokkan
for word, count in counter.items():
    if word in hard_skills_keywords:
        hard_skills_result.append((word, count))
    elif word in soft_skills_keywords:
        soft_skills_result.append((word, count))

# 4. Urutkan berdasarkan frekuensi (count) dari yang paling tinggi ke rendah
hard_skills_result.sort(key=lambda x: x[1], reverse=True)
soft_skills_result.sort(key=lambda x: x[1], reverse=True)

# 5. Tampilkan hasilnya (Misal: Top 20)
print("=== TOP HARD SKILLS ===")
for word, count in hard_skills_result[:20]:
    print(f"{word}: {count}")

print("\n=== TOP SOFT SKILLS ===")
for word, count in soft_skills_result[:20]:
    print(f"{word}: {count}")