import os
import re
import pandas as pd
import numpy as np
from netCDF4 import Dataset
from tqdm import tqdm

# === CONFIG ===
data_dir = "data"
flux_csv_file = "oulu_flux.csv"
output_csv_file = "merged_modis_oulu_with_chl.csv"

# Bounding box: South Australia coastal region
lon_min, lon_max = 130, 142    # degrees East
lat_min, lat_max = -38, -30    # degrees South (negative)

# === Step 1: Scan MODIS .nc Files and Extract Dates ===
def extract_date(fname):
    match = re.search(r'\.(\d{8})\.', fname)
    if match:
        return pd.to_datetime(match.group(1), format="%Y%m%d")
    return None

modis_files = sorted([
    f for f in os.listdir(data_dir) if f.endswith(".nc")
])

modis_df = pd.DataFrame({
    "filename": modis_files,
    "date": [extract_date(f) for f in modis_files]
})

# === Step 2: Read and Clean Oulu Flux CSV ===
flux_df = pd.read_csv(flux_csv_file)

flux_df.rename(columns={
    "Timestamp": "timestamp",
    "CorrectedCountRate[cts/min]": "corrected_flux"
}, inplace=True)

flux_df["date"] = pd.to_datetime(flux_df["timestamp"]).dt.tz_localize(None)
flux_df = flux_df[["date", "corrected_flux"]]

# === Step 3: Merge MODIS + Oulu Data ===
merged = pd.merge(modis_df, flux_df, on="date", how="inner")

# === Step 4: Extract chlor_a Mean from .nc Files WITH bounding box ===
chlor_means = []

print(f"\nProcessing {len(merged)} MODIS files...")

for fname in tqdm(merged["filename"], desc="Reading chlorophyll-a", unit="file"):
    full_path = os.path.join(data_dir, fname)
    try:
        with Dataset(full_path, mode='r') as nc:
            chl = nc.variables["chlor_a"][:]
            lats = nc.variables["lat"][:]
            lons = nc.variables["lon"][:]

            # Find indices for bounding box
            lat_inds = np.where((lats >= lat_min) & (lats <= lat_max))[0]
            lon_inds = np.where((lons >= lon_min) & (lons <= lon_max))[0]

            # Extract region
            region_chl = chl[np.ix_(lat_inds, lon_inds)]

            # Mask invalid or non-ocean pixels
            region_chl = np.ma.masked_invalid(region_chl)
            region_chl = np.ma.masked_where(region_chl <= 0, region_chl)

            mean_val = float(region_chl.mean())
            chlor_means.append(mean_val)
    except Exception as e:
        print(f"\n⚠️ Error reading {fname}: {e}")
        chlor_means.append(np.nan)

# === Step 5: Finalize ===
merged["chlorophyll_mean"] = chlor_means
merged.to_csv(output_csv_file, index=False)

print(f"\n✅ Done. Output saved to: {output_csv_file}")
print(merged.head())
