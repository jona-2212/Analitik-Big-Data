import pandas as pd
from collections import Counter
import re

df = pd.read_csv("cleaning/jobs_cleaned.csv")

all_text = " ".join(
    df["job_requirements"]
    .fillna("")
    .astype(str)
    .str.lower()
)

words = re.findall(r'\b[a-zA-Z0-9+#./]+\b', all_text)

counter = Counter(words)

print(counter.most_common())