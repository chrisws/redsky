import os
import glob
import numpy as np
import pandas as pd
from netCDF4 import Dataset
from tqdm import tqdm
from datetime import datetime

# Bounding box
LAT_MIN, LAT_MAX = -39, -34
LON_MIN, LON_MAX = 136, 142

def extract_bounded_mean(dataset, variable):
    lat = dataset.variables['lat'][:]
    lon = dataset.variables['lon'][:]
    data = dataset.variables[variable][:]

    # Find index ranges within bounding box
    lat_inds = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_inds = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]

    # Check for 2D vs 3D
    if data.ndim == 3:
        data_slice = data[0, lat_inds.min():lat_inds.max()+1, lon_inds.min():lon_inds.max()+1]
    else:
        data_slice = data[lat_inds.min():lat_inds.max()+1, lon_inds.min():lon_inds.max()+1]

    bounded = data_slice[np.isfinite(data_slice)]
    return np.mean(bounded) if bounded.size > 0 else np.nan

def parse_date_from_filename(fname):
    parts = fname.split('.')
    return datetime.strptime(parts[1], "%Y%m%d")

# Load chlorophyll data
chl_files = sorted(glob.glob("data/chlorophyll/*.nc"))
chl_data = []

print("Processing chlorophyll files...")
for f in tqdm(chl_files):
    try:
        ds = Dataset(f)
        mean_chl = extract_bounded_mean(ds, 'chlor_a')
        ds.close()
        chl_data.append({
            "date": parse_date_from_filename(f),
            "chlor_a": mean_chl
        })
    except Exception as e:
        print(f"Error processing {f}: {e}")

chl_df = pd.DataFrame(chl_data)

# Load SST4 data
sst_files = sorted(glob.glob("data/sst4/*.nc"))
sst_data = []

print("Processing SST4 files...")
for f in tqdm(sst_files):
    try:
        ds = Dataset(f)
        mean_sst = extract_bounded_mean(ds, 'sst4')
        ds.close()
        sst_data.append({
            "date": parse_date_from_filename(f),
            "sst4": mean_sst
        })
    except Exception as e:
        print(f"Error processing {f}: {e}")

sst_df = pd.DataFrame(sst_data)

# Merge chlorophyll and SST
merged_df = pd.merge(chl_df, sst_df, on="date", how="outer")

# Load Oulu neutron flux data
# flux_df = pd.read_csv("data/oulu_flux.csv", parse_dates=["Timestamp"])

# #flux_df.rename(columns={"Timestamp": "date", "CorrectedCountRate[cts/min]": "flux"}, inplace=True)
# flux_df.rename(columns={"Timestamp": "timestamp", "CorrectedCountRate[cts/min]": "corrected_flux"}, inplace=True)

# flux_df["date"] = pd.to_datetime(flux_df["timestamp"]).dt.tz_localize(None)
# flux_df = flux_df[["date", "corrected_flux"]]

# # Merge with flux
# final_df = pd.merge(merged_df, flux_df[["date", "flux"]], on="date", how="left")

# Load Oulu neutron flux data
flux_df = pd.read_csv("data/oulu_flux.csv", parse_dates=["Timestamp"])
flux_df.rename(columns={"Timestamp": "timestamp", "CorrectedCountRate[cts/min]": "flux"}, inplace=True)
flux_df["date"] = pd.to_datetime(flux_df["timestamp"]).dt.tz_localize(None)

# Merge with flux
final_df = pd.merge(merged_df, flux_df[["date", "flux"]], on="date", how="left")


# Sort and save
final_df.sort_values("date", inplace=True)
final_df.to_csv("merged_modis_oulu_with_chl_sst4.csv", index=False)
print("Done! Output saved to merged_modis_oulu_with_chl_sst4.csv")
