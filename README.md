# Redsky

## Exploring a possible connection between space weather and the South Australian HAB situation.

### Investigating a Dual-Stressor Hypothesis

We observe recurring phytoplankton (chlorophyll‑a) spikes during May–July off South Australia. These appear preceded by short-term dips in cosmic-ray proton flux (from Oulu neutron monitor), along with concurrent nighttime SST⁴ cooling events tied to Bonney upwelling. Although all patterns align temporally, we emphasize this is a hypothesis-generating analysis, not proof of causation. The aim is to provide an open dataset and visual model, inviting marine ecologists, oceanographers, solar physicists, or space-weather researchers to validate or expand this idea using local data or different geospatial analyses.

<img width="1851" height="901" alt="Screenshot from 2025-08-02 07-43-29" src="https://github.com/user-attachments/assets/646eae52-2eb7-4a16-9583-e602e8337485" />

<img width="1851" height="901" alt="Screenshot from 2025-08-02 07-47-30" src="https://github.com/user-attachments/assets/a5e67350-d82e-427a-9267-f974e02301e5" />

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
