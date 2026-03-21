## Technical Notes

### VIIRS Sensor Capabilities:

- Operational: 2011-present (Suomi-NPP), 2017-present (NOAA-20)
- Resolution: 750m (superior to MODIS 1000m)
- Calibration: Stable, no orbital drift (unlike aging MODIS)
- Algorithm: Standard NASA OC3 chlorophyll-a retrieval
- Validation: Well-established for coastal waters globally

### Not Benthic Reflectance:

- Upper Spencer Gulf depth: 20-40m (adequate for ocean color sensing)
- Gulf St Vincent North depth: 15-30m (adequate for ocean color sensing)
- VIIRS algorithm corrects for shallow-water reflectance
- 13-year temporal stability rules out bottom-type changes
- Southern regions (similar depths) show low stable values
- Spike events (9.11 mg/m³) impossible from benthic reflectance

### Not Cloud/Atmospheric Artifacts:

- 13-year consistent pattern (thousands of clear-sky observations)
- Multiple independent overpasses (NPP + NOAA-20)
- Standard atmospheric correction applied
- Pattern matches known circulation (counter-clockwise GSV)
- Independent validation: In-situ sampling during 2025 crisis confirmed satellite values

## What is Chlorophyll-a?

Chlorophyll-a is the green pigment found in all photosynthetic algae
and plants. In ocean water, measuring chlorophyll-a tells us how much
algae (phytoplankton) is present. It's the standard indicator used
worldwide to monitor algal blooms.

### Understanding the Measurements (mg/m³)

| Chlorophyll-a Level | Interpretation                  | Water Quality |
|---------------------|---------------------------------|---------------|
| 0.1 - 1.0 mg/m³     | Normal oceanic levels           | 🟢 Healthy    |
| 1.0 - 2.0 mg/m³     | Slightly elevated               | 🟡 Acceptable |
| 2.0 - 5.0 mg/m³     | Moderate bloom conditions       | 🟠 Concerning |
| 5.0 - 10.0 mg/m³    | Severe bloom                    | 🔴 Harmful    |
| > 10.0 mg/m³        | Extreme bloom / toxic potential | 🔴 Crisis     |

### What Causes High Chlorophyll?

Algae need nutrients (primarily nitrogen and phosphorus) to grow. Excessive nutrients from:
- Wastewater discharge
- Agricultural fertilizer runoff
- Industrial waste
- Urban stormwater
- Waste management facilities

### Nitrogen Isotope Fingerprinting

- Sample seagrass/algae tissue from north-south transects
- δ15N signatures differentiate: organic waste (+8 to +20‰), treated sewage (+15 to +22‰), natural marine (+3 to +7‰)
- Definitive source apportionment
- For details, see: https://pubmed.ncbi.nlm.nih.gov/23602260/

### Lake Alexandrina

- Refer to the "Chlorophyll-a Time Series Viewer" for an alternative visualisation
- This uses a merged dataset from two satellites (still VIIRS, but NRT) for improved gap filling
- Or just drive down Point Sturt road and see for yourself :)
