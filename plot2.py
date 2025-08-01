import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load CSV
df = pd.read_csv("merged_modis_oulu_with_chl_sst4.csv", parse_dates=["date"])

# Force numeric parsing (coerce invalids to NaN)
for col in ["chlor_a", "sst4", "flux"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Drop any rows that still have missing data
df.dropna(subset=["chlor_a", "sst4", "flux"], inplace=True)

# Z-score normalization
df["chlor_a_z"] = (df["chlor_a"] - df["chlor_a"].mean()) / df["chlor_a"].std()
df["sst4_z"] = (df["sst4"] - df["sst4"].mean()) / df["sst4"].std()
df["flux_z"] = (df["flux"] - df["flux"].mean()) / df["flux"].std()

# Set 'date' as index
df.set_index("date", inplace=True)

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(df.index, df["chlor_a_z"], label="Chlorophyll (z)", color="green")
ax.plot(df.index, df["sst4_z"], label="SST4 (z)", color="orange")
ax.plot(df.index, df["flux_z"], label="Muon Flux (z)", color="blue", alpha=0.6)

# Formatting
ax.set_title("Normalized Time Series: Chlorophyll, SST4, Muon Flux")
ax.set_xlabel("Date")
ax.set_ylabel("Z-score (normalized units)")
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.legend(loc="upper left")
ax.grid(True)
fig.tight_layout()
fig.autofmt_xdate()

plt.show()
