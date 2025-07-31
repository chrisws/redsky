import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("merged_modis_oulu_with_chl.csv")

df["chlor_a_norm"] = df["chlorophyll_mean"] / df["chlorophyll_mean"].max()
df["flux_norm"] = df["corrected_flux"] / df["corrected_flux"].max()

plt.figure(figsize=(10, 5))
plt.plot(df["date"], df["chlor_a_norm"], label="Chlorophyll-a (normalized)")
plt.plot(df["date"], df["flux_norm"], label="Muon Flux (normalized)")
plt.xlabel("Date")
plt.ylabel("Normalized Value (0–1)")
plt.title("Normalized Chlorophyll-a vs Muon Flux")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

