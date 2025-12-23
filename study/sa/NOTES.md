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

## GAB as an Early Warning System for Coastal Algal Blooms

The Great Australian Bight (GAB) serves as an ideal sentinel station
for detecting large-scale algal bloom events along the South
Australian coast. Unlike eastern coastal regions that experience
frequent blooms driven by complex interactions between land-based
nutrient runoff and seasonal upwelling, GAB maintains a
characteristically low and stable chlorophyll-a concentration (~0.4
mg/m³). This oligotrophic baseline, combined with GAB's western
geographic position and isolation from terrestrial nutrient sources,
creates a monitoring location with exceptionally high signal-to-noise
ratio. When GAB experiences significant chlorophyll elevation, it
reliably indicates a major oceanographic forcing event rather than
localized phenomena.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WHY GAB WORKS AS A SENTINEL                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📍 LOCATION              🔬 CHARACTERISTICS         📊 SIGNAL QUALITY  │
│  • Western position       • Low baseline (~0.4)      • High SNR         │
│  • Upstream of coast      • Stable 2017-2023         • Rare false +     │
│  • Deep water access      • No land runoff           • Clear threshold  │
│  • First to see events    • Simple ecosystem         • Easy interpret   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         ALERT FRAMEWORK                                 │
├──────────────────┬──────────────────────┬───────────────────────────────┤
│   TIER 1: Watch  │   TIER 2: Warning    │   TIER 3: Major Event         │
├──────────────────┼──────────────────────┼───────────────────────────────┤
│  > 0.9 mg/m³     │   > 2.0 mg/m³        │   > 4.0 mg/m³                 │
│  (2x baseline)   │   (5x baseline)      │   (10x baseline)              │
│                  │                      │                               │
│  ⚠️  Monitor     │   🚨 Surveillance    │   🔴 Full Response            │
│  • Check weekly  │   • Model trajectory │   • Coastwide event likely    │
│  • Review winds  │   • Prep advisories  │   • 6-9 month lead time       │
│  • Track SST     │   • Alert stakehldrs │   • Issue public warnings     │
└──────────────────┴──────────────────────┴───────────────────────────────┘

                        2024 CASE EXAMPLE
        ┌───────────────────────────────────────────────────┐
        │  June 8, 2024: GAB = 10.02 mg/m³ (23x baseline!)  │
        │                        ↓                          │
        │         [TIER 3 THRESHOLD EXCEEDED]               │
        │            ⚠️ Signal unmonitored                  │
        │                        ↓                          │
        │     Bloom develops through winter/spring 2024     │
        │                        ↓                          │
        │      March 2025: Surfers report on Facebook       │
        │         (~9 months after GAB spike)               │
        │                        ↓                          │
        │         Public awareness & investigation          │
        └───────────────────────────────────────────────────┘

KEY ADVANTAGES                        OPERATIONAL BENEFITS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Single station monitoring           ✓ Simple, actionable system
✓ Clear interpretation                ✓ No complex models needed
✓ Distinguishes event types           ✓ Months of warning time
✓ Low false alarm rate                ✓ Cost-effective implementation

        GAB QUIET + Spencer Gulf HIGH  →  Land runoff event
        GAB HIGH + Coastal regions HIGH →  Ocean-driven (2024 type)
```
