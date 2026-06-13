import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# Set page config
st.set_page_config(page_title="Job Market Analytics", page_icon="📊", layout="wide")

# Title
st.title("📊 Indonesia Job Market Analytics Dashboard")
st.markdown("Dashboard ini menganalisis permintaan skill, gaji, dan tren pekerjaan berdasarkan data yang di-scrape dari platform lowongan kerja (Glints, LinkedIn, Karir.com).")

# ==========================================
# 1. LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("cleaning/jobs_cleaned.csv")
        
        # Tambahan kolom "city"
        def extract_city(location):
            if pd.isna(location): return "Unknown"
            loc = str(location).lower()
            if any(x in loc for x in ["jakarta", "kebayoran", "menteng", "kuningan", "senayan", "sudirman"]): return "Jakarta"
            elif "surabaya" in loc: return "Surabaya"
            elif "bandung" in loc: return "Bandung"
            elif "semarang" in loc: return "Semarang"
            elif "tangerang" in loc: return "Tangerang"
            elif "bekasi" in loc: return "Bekasi"
            elif "denpasar" in loc: return "Denpasar"
            elif "medan" in loc: return "Medan"
            else: return "Lainnya"
            
        df["city"] = df["location"].apply(extract_city)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

df = load_data()

if df is None:
    st.stop()

# ==========================================
# DEFINISI SKILL UNTUK EKSTRAKSI
# ==========================================
SKILL_PATTERNS = {
    # Hard Skills
    "Excel/Office": r'\bexcel\b|\bmicrosoft\b|\boffice\b',
    "Sales/Marketing": r'\bsales\b|\bmarketing\b',
    "SQL/Database": r'\bsql\b|\bmysql\b|\bdatabase\b',
    "Python": r'\bpython\b',
    "SAP/ERP": r'\bsap\b|\berp\b',
    "Design/UI-UX": r'\bdesign\b|\bdesain\b|\bfigma\b|\bui\b|\bux\b',
    "Accounting": r'\baccounting\b|\bkeuangan\b|\bfinance\b',
    "Digital Marketing": r'\bseo\b|\bdigital\b|\bads\b',
    "Cloud (AWS/Azure)": r'\baws\b|\bazure\b|\bcloud\b',
    "Java": r'\bjava\b',
    
    # Soft Skills
    "Communication": r'\bkomunikasi\b|\bcommunication\b',
    "Teamwork": r'\btim\b|\bteam\b|\bteamwork\b',
    "Leadership": r'\bleadership\b|\bkepemimpinan\b',
    "English": r'\binggris\b|\benglish\b',
    "Detail Oriented": r'\bteliti\b|\bdetail\b',
    "Problem Solving": r'\bproblem\b|\bsolving\b',
}

# Ekstrak skills
text_col = df["job_requirements"].fillna("").astype(str).str.lower()
for label, pattern in SKILL_PATTERNS.items():
    df[f"sk_{label}"] = text_col.str.contains(pattern, regex=True).astype(int)

# ==========================================
# 2. METRICS OVERVIEW
# ==========================================
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Lowongan", f"{len(df)}")
col2.metric("Total Perusahaan", f"{df['company_name'].nunique()}")
if df["salary_avg_numeric"].notna().sum() > 0:
    avg_sal = df["salary_avg_numeric"].mean() / 1_000_000
    col3.metric("Rata-rata Gaji", f"Rp {avg_sal:.1f} Juta")
col4.metric("Sumber Platform", f"{df['source_platform'].nunique()}")

# ==========================================
# 3. ANALISIS SKILL (SKILL DEMAND)
# ==========================================
st.markdown("---")
st.header("1️⃣ Analisis Permintaan Skill")

# Hitung total kemunculan tiap skill
skill_counts = []
for label in SKILL_PATTERNS.keys():
    count = df[f"sk_{label}"].sum()
    skill_counts.append({"Skill": label, "Jumlah": count})

skill_df = pd.DataFrame(skill_counts).sort_values("Jumlah", ascending=True)

fig_skills = px.bar(
    skill_df, 
    x="Jumlah", y="Skill", 
    orientation='h', 
    title="Top Skills yang Paling Sering Diminta",
    color="Jumlah",
    color_continuous_scale=px.colors.sequential.Blues
)
st.plotly_chart(fig_skills, use_container_width=True)

# ==========================================
# 4. GAJI VS SKILL & PENGALAMAN
# ==========================================
st.markdown("---")
st.header("2️⃣ Analisis Gaji")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Gaji Berdasarkan Level Pengalaman")
    # Filter dan hitung rata-rata
    salary_exp = df[df["salary_avg_numeric"].notna()].groupby("experience_group")["salary_avg_numeric"].mean().reset_index()
    salary_exp["Gaji (Juta)"] = salary_exp["salary_avg_numeric"] / 1_000_000
    salary_exp = salary_exp.sort_values("Gaji (Juta)", ascending=False)
    
    fig_sal_exp = px.bar(
        salary_exp, 
        x="experience_group", y="Gaji (Juta)",
        color="experience_group",
        title="Rata-rata Gaji per Experience Level"
    )
    st.plotly_chart(fig_sal_exp, use_container_width=True)

with col2:
    st.subheader("Gaji Berdasarkan Minimum Pendidikan")
    salary_edu = df[df["salary_avg_numeric"].notna()].groupby("education_min")["salary_avg_numeric"].mean().reset_index()
    salary_edu["Gaji (Juta)"] = salary_edu["salary_avg_numeric"] / 1_000_000
    salary_edu = salary_edu.sort_values("Gaji (Juta)", ascending=False)
    
    fig_sal_edu = px.bar(
        salary_edu, 
        x="education_min", y="Gaji (Juta)",
        color="education_min",
        title="Rata-rata Gaji per Syarat Pendidikan"
    )
    st.plotly_chart(fig_sal_edu, use_container_width=True)

st.subheader("Rata-rata Gaji Berdasarkan Skill Tertentu")
# Hitung rata-rata gaji untuk lowongan yang mencantumkan skill vs tidak
salary_skill_data = []
salary_df = df[df["salary_avg_numeric"].notna()]

for label in SKILL_PATTERNS.keys():
    has_skill_salary = salary_df[salary_df[f"sk_{label}"] == 1]["salary_avg_numeric"].mean()
    if pd.notna(has_skill_salary):
        salary_skill_data.append({"Skill": label, "Gaji Rata-rata (Juta)": has_skill_salary / 1_000_000})

if salary_skill_data:
    salary_skill_df = pd.DataFrame(salary_skill_data).sort_values("Gaji Rata-rata (Juta)", ascending=False)
    fig_sal_skill = px.bar(
        salary_skill_df,
        x="Skill", y="Gaji Rata-rata (Juta)",
        color="Gaji Rata-rata (Juta)",
        color_continuous_scale=px.colors.sequential.Oranges,
        title="Skill dengan Gaji Rata-rata Tertinggi"
    )
    st.plotly_chart(fig_sal_skill, use_container_width=True)

# ==========================================
# 5. DEMOGRAFI & LOKASI
# ==========================================
st.markdown("---")
st.header("3️⃣ Analisis Geografis & Demografi")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribusi Lokasi Pekerjaan")
    city_counts = df["city"].value_counts().reset_index()
    city_counts.columns = ["Kota", "Jumlah"]
    
    fig_city = px.pie(
        city_counts, 
        values="Jumlah", names="Kota",
        title="Persentase Lowongan Berdasarkan Kota",
        hole=0.4
    )
    st.plotly_chart(fig_city, use_container_width=True)

with col2:
    st.subheader("Distribusi Platform Sumber")
    platform_counts = df["source_platform"].value_counts().reset_index()
    platform_counts.columns = ["Platform", "Jumlah"]
    
    fig_plat = px.pie(
        platform_counts, 
        values="Jumlah", names="Platform",
        title="Sumber Platform Lowongan Kerja",
        hole=0.4
    )
    st.plotly_chart(fig_plat, use_container_width=True)

# ==========================================
# 6. RAW DATA (Optional)
# ==========================================
st.markdown("---")
with st.expander("Tampilkan Raw Data"):
    st.dataframe(df[["job_title", "company_name", "location", "salary_range", "experience_level", "education_min"]])

st.markdown("""
    <div style='text-align: center; margin-top: 50px; color: grey;'>
        <small>Dibuat untuk Project Big Data Analytics | Data Source: LinkedIn, Glints, Karir.com</small>
    </div>
""", unsafe_allow_html=True)
