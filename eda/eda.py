import pandas as pd

df = pd.read_csv("cleaning/jobs_cleaned.csv")

print("="*50)
print("INFO DATASET")
print("="*50)

print("\nShape:")
print(df.shape)

print("\nKolom:")
print(df.columns.tolist())

print("\nMissing Value:")
print(df.isnull().sum())

print("\nDuplikat:")
print(df.duplicated().sum())

print("\nJumlah Lowongan per Platform")

print(
    df["source_platform"]
    .value_counts()
)

print("\nTop 10 Job Title")

print(
    df["job_title"]
    .value_counts()
    .head(10)
)

print("\nEducation Requirement")

print(
    df["education_req"]
    .value_counts(dropna=False)
)

print("\nExperience Level")

print(
    df["experience_level"]
    .value_counts(dropna=False)
)

print("\nJob Type")

print(
    df["job_type"]
    .value_counts(dropna=False)
)

print(df["experience_group"].value_counts())