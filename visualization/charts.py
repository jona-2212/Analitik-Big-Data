import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import re
import os
from collections import Counter

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.size'] = 10

# =========================
# LOAD DATA
# =========================
df = pd.read_csv("cleaning/jobs_cleaned.csv")

# Buat folder output
os.makedirs("visualization/charts", exist_ok=True)

# =========================
# HELPER: Warna Gradient
# =========================
COLORS_BLUE = ['#1a237e', '#283593', '#303f9f', '#3949ab', '#3f51b5',
               '#5c6bc0', '#7986cb', '#9fa8da', '#c5cae9', '#e8eaf6']
COLORS_WARM = ['#e65100', '#ef6c00', '#f57c00', '#fb8c00', '#ff9800',
               '#ffa726', '#ffb74d', '#ffcc80', '#ffe0b2', '#fff3e0']
COLORS_GREEN = ['#1b5e20', '#2e7d32', '#388e3c', '#43a047', '#4caf50',
                '#66bb6a', '#81c784', '#a5d6a7', '#c8e6c9', '#e8f5e9']
COLORS_DUAL = ['#1565c0', '#ef6c00']  # Blue vs Orange

def save_chart(fig, name):
    path = f"visualization/charts/{name}.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  ✅ Saved: {path}")


# ===========================================================
# CHART 1: Top 15 Hard Skills & Soft Skills (Horizontal Bar)
# ===========================================================
print("📊 Chart 1: Top Hard Skills & Soft Skills...")

HARD_SKILLS = {
    'excel', 'microsoft', 'office', 'word', 'powerpoint',
    'python', 'java', 'php', 'javascript', 'react', 'sql', 'mysql',
    'database', 'tableau', 'sap', 'erp', 'seo', 'sem', 'digital',
    'accounting', 'finance', 'keuangan', 'teknik', 'komputer',
    'software', 'ui', 'ux', 'design', 'desain', 'pemasaran',
    'cloud', 'aws', 'azure', 'docker', 'git', 'linux',
    'figma', 'photoshop', 'laravel', 'node.js', 'html', 'css',
    'mongodb', 'kubernetes', 'c#', 'c++', 'sales', 'marketing',
}

SOFT_SKILLS = {
    'komunikasi', 'communication', 'tim', 'team', 'teamwork', 'kolaborasi',
    'teliti', 'detail', 'jujur', 'disiplin', 'gigih', 'kreatif', 'creative',
    'mandiri', 'independent', 'leadership', 'kepemimpinan', 'problem',
    'solving', 'analitis', 'inggris', 'english',
    'interpersonal', 'negotiation', 'negoisasi',
    'presentasi', 'presentation', 'inovatif', 'innovative',
}

all_text = " ".join(df["job_requirements"].fillna("").astype(str).str.lower())
words = re.findall(r'\b[a-zA-Z0-9+#./]+\b', all_text)
counter = Counter(words)

hard_data = [(w, c) for w, c in counter.items() if w in HARD_SKILLS]
soft_data = [(w, c) for w, c in counter.items() if w in SOFT_SKILLS]
hard_data.sort(key=lambda x: x[1], reverse=True)
soft_data.sort(key=lambda x: x[1], reverse=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
fig.suptitle("Top Skills yang Dicari di Pasar Kerja Indonesia", fontsize=16, fontweight='bold', y=1.02)

# Hard Skills
top_hard = hard_data[:12]
labels_h = [x[0] for x in top_hard][::-1]
values_h = [x[1] for x in top_hard][::-1]
colors_h = COLORS_BLUE[:len(labels_h)][::-1]
ax1.barh(labels_h, values_h, color=colors_h, edgecolor='white', height=0.7)
ax1.set_title("🔧 Hard Skills", fontsize=13, fontweight='bold', pad=10)
ax1.set_xlabel("Frekuensi")
for i, v in enumerate(values_h):
    ax1.text(v + 0.5, i, str(v), va='center', fontsize=9, fontweight='bold')
ax1.spines[['top', 'right']].set_visible(False)

# Soft Skills
top_soft = soft_data[:12]
labels_s = [x[0] for x in top_soft][::-1]
values_s = [x[1] for x in top_soft][::-1]
colors_s = COLORS_WARM[:len(labels_s)][::-1]
ax2.barh(labels_s, values_s, color=colors_s, edgecolor='white', height=0.7)
ax2.set_title("🤝 Soft Skills", fontsize=13, fontweight='bold', pad=10)
ax2.set_xlabel("Frekuensi")
for i, v in enumerate(values_s):
    ax2.text(v + 0.5, i, str(v), va='center', fontsize=9, fontweight='bold')
ax2.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
save_chart(fig, "01_top_skills")


# ===========================================================
# CHART 2: Distribusi Experience Group (Pie + Bar)
# ===========================================================
print("📊 Chart 2: Distribusi Experience Group...")

exp_counts = df["experience_group"].value_counts()
# Hilangkan Unknown agar lebih informatif
exp_counts = exp_counts.drop("Unknown", errors="ignore")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Distribusi Level Pengalaman di Lowongan Kerja", fontsize=14, fontweight='bold')

colors_pie = ['#1565c0', '#43a047', '#ef6c00', '#d32f2f'][:len(exp_counts)]
wedges, texts, autotexts = ax1.pie(
    exp_counts.values, labels=exp_counts.index, autopct='%1.1f%%',
    colors=colors_pie, startangle=90, pctdistance=0.8,
    wedgeprops=dict(width=0.5, edgecolor='white')
)
for t in autotexts:
    t.set_fontsize(10)
    t.set_fontweight('bold')
ax1.set_title("Proporsi", fontsize=12)

ax2.bar(exp_counts.index, exp_counts.values, color=colors_pie, edgecolor='white', width=0.6)
for i, v in enumerate(exp_counts.values):
    ax2.text(i, v + 1, str(v), ha='center', fontweight='bold')
ax2.set_title("Jumlah Lowongan", fontsize=12)
ax2.set_ylabel("Jumlah")
ax2.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
save_chart(fig, "02_experience_distribution")


# ===========================================================
# CHART 3: Salary Distribution (Histogram + Box)
# ===========================================================
print("📊 Chart 3: Distribusi Gaji...")

salary_data = df["salary_avg_numeric"].dropna() / 1_000_000  # Convert to juta

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Distribusi Gaji Rata-rata Lowongan Kerja", fontsize=14, fontweight='bold')

ax1.hist(salary_data, bins=20, color='#1565c0', edgecolor='white', alpha=0.9)
ax1.axvline(salary_data.median(), color='#ef6c00', linestyle='--', linewidth=2, label=f'Median: Rp {salary_data.median():.1f} jt')
ax1.axvline(salary_data.mean(), color='#d32f2f', linestyle='--', linewidth=2, label=f'Mean: Rp {salary_data.mean():.1f} jt')
ax1.set_xlabel("Gaji (Juta Rupiah)")
ax1.set_ylabel("Jumlah Lowongan")
ax1.set_title("Histogram Gaji")
ax1.legend(fontsize=9)
ax1.spines[['top', 'right']].set_visible(False)

# Box plot per experience
exp_order = ["Fresh Graduate", "Junior", "Mid", "Senior"]
salary_by_exp = [df[df["experience_group"] == e]["salary_avg_numeric"].dropna() / 1_000_000 for e in exp_order]
salary_by_exp_filtered = [(data, label) for data, label in zip(salary_by_exp, exp_order) if len(data) > 0]

if salary_by_exp_filtered:
    box_data = [x[0] for x in salary_by_exp_filtered]
    box_labels = [x[1] for x in salary_by_exp_filtered]
    bp = ax2.boxplot(box_data, labels=box_labels, patch_artist=True, widths=0.5)
    box_colors = ['#1565c0', '#43a047', '#ef6c00', '#d32f2f']
    for patch, color in zip(bp['boxes'], box_colors[:len(bp['boxes'])]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax2.set_ylabel("Gaji (Juta Rupiah)")
    ax2.set_title("Gaji per Experience Level")
    ax2.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
save_chart(fig, "03_salary_distribution")


# ===========================================================
# CHART 4: Skill vs Experience Level (Grouped Bar)
# ===========================================================
print("📊 Chart 4: Skill per Experience Level...")

SKILL_PATTERNS = {
    "Excel/Office":    r'\bexcel\b|\bmicrosoft\b|\boffice\b',
    "Sales/Marketing": r'\bsales\b|\bmarketing\b',
    "Communication":   r'\bkomunikasi\b|\bcommunication\b',
    "Teamwork":        r'\btim\b|\bteam\b|\bteamwork\b',
    "SQL/Database":    r'\bsql\b|\bmysql\b|\bdatabase\b',
    "Python":          r'\bpython\b',
    "SAP/ERP":         r'\bsap\b|\berp\b',
    "Design/UI-UX":    r'\bdesign\b|\bdesain\b|\bfigma\b',
    "Accounting":      r'\baccounting\b|\bkeuangan\b',
    "Leadership":      r'\bleadership\b|\bkepemimpinan\b',
}

text_col = df["job_requirements"].fillna("").astype(str).str.lower()
for label, pattern in SKILL_PATTERNS.items():
    df[f"sk_{label}"] = text_col.str.contains(pattern, regex=True).astype(int)

exp_groups = ["Fresh Graduate", "Junior", "Mid", "Senior"]
skill_labels = list(SKILL_PATTERNS.keys())

# Hitung persentase
data_matrix = []
for exp in exp_groups:
    exp_df = df[df["experience_group"] == exp]
    if len(exp_df) == 0:
        data_matrix.append([0] * len(skill_labels))
        continue
    row = []
    for sk in skill_labels:
        pct = exp_df[f"sk_{sk}"].sum() / len(exp_df) * 100
        row.append(round(pct, 1))
    data_matrix.append(row)

fig, ax = plt.subplots(figsize=(14, 6))
fig.suptitle("Persentase Skill Diminta per Level Pengalaman", fontsize=14, fontweight='bold')

x = np.arange(len(skill_labels))
width = 0.2
exp_colors = ['#1565c0', '#43a047', '#ef6c00', '#d32f2f']

for i, (exp, values) in enumerate(zip(exp_groups, data_matrix)):
    offset = (i - 1.5) * width
    bars = ax.bar(x + offset, values, width, label=exp, color=exp_colors[i], edgecolor='white')

ax.set_xlabel("Skill")
ax.set_ylabel("% Lowongan yang Meminta Skill Ini")
ax.set_xticks(x)
ax.set_xticklabels(skill_labels, rotation=35, ha='right', fontsize=9)
ax.legend(title="Experience", fontsize=9)
ax.spines[['top', 'right']].set_visible(False)
ax.set_ylim(0, max(max(row) for row in data_matrix if row) * 1.2)

plt.tight_layout()
save_chart(fig, "04_skill_by_experience")


# ===========================================================
# CHART 5: Education Distribution
# ===========================================================
print("📊 Chart 5: Distribusi Pendidikan...")

edu_counts = df["education_min"].value_counts()

fig, ax = plt.subplots(figsize=(8, 5))
colors_edu = ['#1565c0', '#1976d2', '#1e88e5', '#42a5f5', '#64b5f6'][:len(edu_counts)]
bars = ax.bar(edu_counts.index, edu_counts.values, color=colors_edu, edgecolor='white', width=0.6)
for bar, val in zip(bars, edu_counts.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, str(val),
            ha='center', fontweight='bold', fontsize=11)
ax.set_title("Distribusi Syarat Pendidikan Minimum", fontsize=14, fontweight='bold')
ax.set_ylabel("Jumlah Lowongan")
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
save_chart(fig, "05_education_distribution")


# ===========================================================
# CHART 6: Salary vs Skill (Lollipop Chart)
# ===========================================================
print("📊 Chart 6: Gaji per Skill...")

salary_df = df[df["salary_avg_numeric"].notna()].copy()
skill_salary = []

for label, pattern in SKILL_PATTERNS.items():
    has = salary_df[salary_df[f"sk_{label}"] == 1]["salary_avg_numeric"]
    if len(has) >= 3:
        skill_salary.append({"skill": label, "avg_salary": has.mean() / 1_000_000, "count": len(has)})

skill_salary_df = pd.DataFrame(skill_salary).sort_values("avg_salary", ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))
y_pos = range(len(skill_salary_df))

ax.hlines(y=y_pos, xmin=0, xmax=skill_salary_df["avg_salary"].values, color='#bdbdbd', linewidth=2)
ax.scatter(skill_salary_df["avg_salary"].values, y_pos, color='#1565c0', s=120, zorder=3, edgecolors='white', linewidth=2)

for i, (_, row) in enumerate(skill_salary_df.iterrows()):
    ax.text(row["avg_salary"] + 0.15, i, f'Rp {row["avg_salary"]:.1f} jt', va='center', fontsize=9, fontweight='bold')

ax.set_yticks(list(y_pos))
ax.set_yticklabels(skill_salary_df["skill"].values)
ax.set_xlabel("Rata-rata Gaji (Juta Rupiah)")
ax.set_title("Rata-rata Gaji Berdasarkan Skill yang Diminta", fontsize=14, fontweight='bold')
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
save_chart(fig, "06_salary_by_skill")


# ===========================================================
# CHART 7: Lowongan per Platform
# ===========================================================
print("📊 Chart 7: Lowongan per Platform...")

platform_counts = df["source_platform"].value_counts()

fig, ax = plt.subplots(figsize=(7, 5))
colors_plat = ['#1565c0', '#43a047', '#ef6c00']
ax.bar(platform_counts.index, platform_counts.values, color=colors_plat[:len(platform_counts)], 
       edgecolor='white', width=0.5)
for i, v in enumerate(platform_counts.values):
    ax.text(i, v + 2, str(v), ha='center', fontweight='bold', fontsize=12)
ax.set_title("Jumlah Lowongan per Platform", fontsize=14, fontweight='bold')
ax.set_ylabel("Jumlah")
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
save_chart(fig, "07_platform_distribution")


# ===========================================================
# CHART 8: Hard vs Soft Skill Ratio
# ===========================================================
print("📊 Chart 8: Rasio Hard vs Soft Skill...")

# Hitung total per lowongan
hard_pattern = '|'.join([p for p in SKILL_PATTERNS.values()][:5])  # first 5 are hard-ish
soft_pattern = r'\bkomunikasi\b|\bcommunication\b|\btim\b|\bteam\b|\bjujur\b|\bteliti\b|\bdisiplin\b|\bleadership\b'

hard_count_per_exp = []
soft_count_per_exp = []

for exp in exp_groups:
    exp_df = df[df["experience_group"] == exp]
    if len(exp_df) == 0:
        hard_count_per_exp.append(0)
        soft_count_per_exp.append(0)
        continue
    h = exp_df[[c for c in exp_df.columns if c.startswith("sk_") and any(x in c for x in ["Excel", "Sales", "SQL", "Python", "SAP", "Design", "Accounting"])]].sum().sum()
    s = exp_df[[c for c in exp_df.columns if c.startswith("sk_") and any(x in c for x in ["Communication", "Teamwork", "Leadership"])]].sum().sum()
    hard_count_per_exp.append(int(h))
    soft_count_per_exp.append(int(s))

fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(exp_groups))
width = 0.35
ax.bar(x - width/2, hard_count_per_exp, width, label='Hard Skills', color='#1565c0', edgecolor='white')
ax.bar(x + width/2, soft_count_per_exp, width, label='Soft Skills', color='#ef6c00', edgecolor='white')
ax.set_xticks(x)
ax.set_xticklabels(exp_groups)
ax.set_ylabel("Total Kemunculan Skill")
ax.set_title("Hard Skills vs Soft Skills per Experience Level", fontsize=14, fontweight='bold')
ax.legend()
ax.spines[['top', 'right']].set_visible(False)

plt.tight_layout()
save_chart(fig, "08_hard_vs_soft_ratio")


print("\n" + "=" * 60)
print("✅ SEMUA CHART BERHASIL DIBUAT!")
print("=" * 60)
print(f"📁 Lokasi: visualization/charts/")
print(f"📊 Total: 8 chart")
