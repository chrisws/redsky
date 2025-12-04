import pandas as pd
import numpy as np
import sys

if len(sys.argv) != 2:
    print ("viirs_yearly_mean chlr-a.csv")
    exit(1)

# --- 1. Read CSV ---
df = pd.read_csv(sys.argv[1])

# Read and parse data
date_col = df.columns[0]
dates = pd.to_datetime(df[date_col].astype(str), format='%Y%m%d')

df['Year'] = dates.dt.year
df['Quarter'] = dates.dt.quarter
df = df.drop(columns=[date_col])

# Determine the most recent three years
latest_years = sorted(df['Year'].unique())[-3:]

# Create group labels (year vs year+quarter) - ensure Year is int
df['Group'] = df.apply(
    lambda row: f"{int(row['Year'])}Q{int(row['Quarter'])}" if row['Year'] in latest_years else str(int(row['Year'])),
    axis=1
)

# Filter out the last quarter of the most recent year
#latest_year = max(latest_years)
#latest_quarter = df[df['Year'] == latest_year]['Quarter'].max()
#df = df[~((df['Year'] == latest_year) & (df['Quarter'] == latest_quarter))]

# Drop Year and Quarter columns before aggregating
df = df.drop(columns=['Year', 'Quarter'])

# Geometric mean for chlorophyll-a (standard for log-normal distributions)
def geometric_mean(x):
    x = x[~x.isna()]
    if len(x) > 0:
        return np.exp(np.log(x).mean())
    return np.nan

# Group and aggregate
group_means = df.groupby('Group').agg(geometric_mean)

# Sort chronologically
def sort_key(label):
    label = str(label).strip()
    if 'Q' in label:
        y, q = label.split('Q')
        return (int(y), int(q))
    return (int(label), 0)

group_means = group_means.sort_index(key=lambda idx: [sort_key(i) for i in idx])

# Add grand geometric mean
group_means.loc['Grand Mean'] = group_means.apply(geometric_mean)

# Format and output as markdown
pd.set_option('display.float_format', '{:.2f}'.format)
print(group_means.to_markdown())
