# 📊 Implementasi Pipeline Preprocessing dan Analitik Pasar Kerja Indonesia Menggunakan Ekosistem Big Data Berbasis Karakteristik 5V

Proyek Big Data Analytics ini bertujuan untuk mengumpulkan, membersihkan, menganalisis, dan memvisualisasikan data lowongan pekerjaan dari berbagai platform (Glints, LinkedIn, Karir.com). Proyek ini menyoroti keahlian (*skills*) apa saja yang paling banyak dicari oleh perusahaan di Indonesia, korelasi gaji dengan tingkat keahlian/pendidikan, serta sebaran geografis lapangan kerja.

## 🗂️ Struktur Proyek
```text
📦 abd/
 ┣ 📂 scrapping/       # Script untuk scraping data dari platform lowongan kerja
 ┣ 📂 cleaning/        # Pre-processing & standarisasi data (jobs_cleaned.csv)
 ┣ 📂 eda/             # Exploratory Data Analysis & penyaringan keyword
 ┣ 📂 analysis/        # Analisis mendalam (Hard vs Soft Skills, Gaji, Geografis)
 ┣ 📂 visualization/   # Visualisasi statis (matplotlib) & Dashboard (Streamlit)
 ┗ 📜 README.md
```

## 🛠️ Prasyarat (Requirements)
Pastikan Anda sudah menginstal Python (minimal versi 3.8+). Anda memerlukan beberapa library pihak ketiga untuk menjalankan seluruh analisis dan visualisasi.

Jalankan perintah ini di terminal Anda untuk menginstal dependencies:
```bash
pip install pandas matplotlib plotly streamlit
```

### ⚠️ Solusi Error Instalasi Streamlit di Windows
Jika saat menginstal Streamlit Anda menemukan error terkait `Long Path`, ikuti langkah ini:
1. Buka **PowerShell sebagai Administrator**.
2. Jalankan perintah berikut lalu tekan Enter:
   ```powershell
   Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1
   ```
3. Buka ulang terminal project Anda, dan jalankan perintah `pip install` di atas kembali.

---

## 🚀 Cara Menjalankan Project (Dari Awal)

Untuk mereplikasi hasil visualisasi dari tahap paling awal, Anda bisa menjalankan script berikut secara berurutan:

### 1. Data Cleaning
Proses ini akan mengambil data hasil scraping, menghapus duplikat, dan menstandarisasi kolom.
```bash
python cleaning/clean.py
```
*(Menghasilkan file `cleaning/jobs_cleaned.csv`)*

### 2. Proses Analisis
Jalankan ketiga script di bawah ini untuk menghasilkan insight berbentuk data tabular (CSV).
```bash
# Analisis Hard Skills vs Soft Skills per Pendidikan & Pengalaman
python analysis/skill_by_category.py

# Analisis Rata-rata Gaji berdasarkan Keahlian (Top Skills)
python analysis/salary_analysis.py

# Analisis Sebaran Lowongan & Top Skills per Kota
python analysis/geographic_analysis.py
```
*(Menghasilkan beberapa file `.csv` di dalam folder `analysis/`)*

### 3. Visualisasi Statis (Gambar)
Untuk me-render berbagai metrik menjadi grafik gambar (histogram, bar chart, pie chart):
```bash
python visualization/charts.py
```
*(Gambar grafik akan otomatis tersimpan di folder `visualization/charts/`)*

### 4. 🌐 Menjalankan Dashboard Interaktif (Puncak Proyek)
Jika Anda ingin mengeksplorasi data di browser Anda secara interaktif (menggunakan grafik Plotly), jalankan perintah berikut:

```bash
python -m streamlit run visualization/dashboard.py
```
*(Browser akan otomatis terbuka menampilkan antarmuka Dashboard Big Data Analytics)*.
