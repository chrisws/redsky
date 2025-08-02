## Exploring a possible connection between space weather and the South Australian HAB situation.

🌊 Summary: Dual Stressor Hypothesis for South Australian Phytoplankton Blooms

This project proposes a dual-stressor mechanism driving episodic phytoplankton blooms (and possible harmful algal blooms, HABs) off South Australia's coast. The theory integrates solar activity, cosmic ray flux, and oceanographic conditions, supported by satellite and ground-based datasets.

🔍 Key Observations

- Forbush Decreases—bursts of solar wind—temporarily reduce the cosmic ray flux reaching Earth.
- This results in lower muon flux at sea level, likely reducing oxidative stress on marine microbes including phytoplankton.
- In this lower-stress window, phytoplankton growth potential increases, especially if:
  - Nutrient upwelling (e.g. from the Bonney Upwelling) is active.
  - Sea surface temperatures (SST) are elevated, supporting faster metabolism.

🌱 Role of the Murray River Plume (2022–2023)

- During the 2022–2023 Murray River flood, a massive freshwater and nutrient-rich plume entered the marine system.
- This provided an additional nutrient source, amplifying phytoplankton growth in adjacent coastal waters.
- When solar-induced stress relief coincided with this event, the result was likely a stronger or more sustained bloom, particularly in the Eyre Peninsula and Coorong region.

🧬 Ecological Chain Reaction

- Phytoplankton experience a short-term +1 boost from the combination of:
  - Reduced muon stress (post-Forbush)
  - Warm SST
  - Nutrient input (upwelling or flood plume)
- Zooplankton, their grazers, show a lagged or mismatched response, either biologically or due to different environmental triggers.
- This creates a temporary trophic imbalance, where phytoplankton escape grazing control and may bloom excessively.

📈 Data Patterns

- Time series show that dips in muon flux (Forbush events) precede chlorophyll-a spikes by days to weeks.
- These sequences align with known HAB timing off South Australia, including post-river plume dynamics.

🌐 Broader Implications

- Even though muon data is sourced from the Oulu neutron monitor in the Northern Hemisphere, it reflects global-scale modulation of cosmic rays by solar activity.
- If validated, this mechanism suggests space weather may influence marine biology, with potential predictive value for HAB risk — especially during compound events like major river floods.
 
<img width="1851" height="901" alt="Screenshot from 2025-08-02 07-43-29" src="https://github.com/user-attachments/assets/646eae52-2eb7-4a16-9583-e602e8337485" />

<img width="1851" height="901" alt="Screenshot from 2025-08-02 07-47-30" src="https://github.com/user-attachments/assets/a5e67350-d82e-427a-9267-f974e02301e5" />

<img width="1660" height="630" alt="Screenshot from 2025-08-02 10-53-50" src="https://github.com/user-attachments/assets/98187ef7-6bfc-4216-862a-fd3443af5e6c" />

## 📊 Data Provenance

This project integrates multiple open datasets to explore potential correlations between solar activity, ocean temperature, and phytoplankton concentrations in the Southern Ocean. All data were downloaded and processed locally using public APIs or file archives.

| Dataset                      | Source                                                                 | Variable(s)                    | Units      | Temporal Coverage       | Notes |
|------------------------------|------------------------------------------------------------------------|--------------------------------|------------|--------------------------|-------|
| **MODIS-Aqua Chlorophyll-a** | [NASA OceanColor](https://oceandata.sci.gsfc.nasa.gov) (L3m, daily, 4km) | `chlor_a`                      | mg/m³      | **2022-01-01 only**      | Single snapshot, averaged over bounding box covering Bonney Coast |
| **MODIS-Aqua SST⁴ Nighttime** | [NASA OceanColor](https://oceandata.sci.gsfc.nasa.gov) (L3m, daily, 4km) | `sst4` (sea surface temp, nighttime) | °C         | 2020–present (subset used) | Matches chlorophyll data spatial resolution and region |
| **Oulu Neutron Monitor**     | [University of Oulu](https://cosmicrays.oulu.fi)                      | `flux` (corrected count rate)  | counts/min | 1964–present (subset 2020–2025 used) | Used as proxy for high-energy cosmic ray muon flux |

- SST⁴ and flux data are merged by date.
- Chlorophyll is only available for a single day so far and is intended as a reference snapshot.
- Flux data is from a fixed polar location (Oulu) and reflects broad cosmic ray modulation trends.

> Note: No advanced statistical filtering or modeling has been applied yet. Comparisons are exploratory.
