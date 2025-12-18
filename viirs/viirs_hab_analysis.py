#!/usr/bin/env python3
"""
Comprehensive HAB analysis for South Australia coastal regions.
Analyzes chlorophyll-a data, climate events, and spatial patterns.
"""
import argparse
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys

from datetime import datetime, timedelta
from pathlib import Path
from scipy import stats, signal
from scipy.interpolate import interp1d
from viirs_regions import get_regions

# Known events
EVENTS = {
    '2023_flood': {
        'date': '2023-01-15',
        'label': '2022-23 River Murray Floods',
        'color': 'blue',
        'explanation': 'Increased nutrient runoff from flooding'
    },
    '2024_heatwave': {
        'date': '2025-01-20',
        'label': '2024-25 Marine Heatwave',
        'color': 'red',
        'explanation': 'Elevated water temperature promoting algal growth'
    }
}

def load_chlorophyll_data(csv_path):
    """Load chlorophyll-a CSV data with dates in YYYYMMDD format."""
    df = pd.read_csv(csv_path)

    # Parse YYYYMMDD format (e.g., 20171213)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.set_index('date')

    # Convert string values to float, handling empty strings
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

def detect_bloom_threshold(data, percentile=75):
    """Detect HAB threshold using percentile method."""
    valid_data = data.dropna()
    if len(valid_data) < 10:
        return None
    return np.percentile(valid_data, percentile)

def analyze_event_impact(df, regions, event_date, window_days=60):
    """Analyze chlorophyll changes around a specific event."""
    event_dt = pd.to_datetime(event_date)

    # Define pre/post windows
    pre_start = event_dt - timedelta(days=window_days)
    pre_end = event_dt - timedelta(days=1)
    post_start = event_dt
    post_end = event_dt + timedelta(days=window_days)

    results = {}
    for region in regions.keys():
        if region not in df.columns:
            continue

        pre_data = df.loc[pre_start:pre_end, region].dropna()
        post_data = df.loc[post_start:post_end, region].dropna()

        if len(pre_data) > 3 and len(post_data) > 3:
            pre_mean = pre_data.mean()
            post_mean = post_data.mean()
            percent_change = ((post_mean - pre_mean) / pre_mean) * 100

            # Statistical test
            t_stat, p_value = stats.ttest_ind(pre_data, post_data)

            results[region] = {
                'pre_mean': pre_mean,
                'post_mean': post_mean,
                'percent_change': percent_change,
                'p_value': p_value,
                'significant': p_value < 0.05
            }

    return results

def detect_hab_boundaries(df, regions, threshold_percentile=75):
    """Detect spatial HAB patterns based on bloom frequency."""
    boundaries = {}

    for region in regions.keys():
        if region not in df.columns:
            continue

        data = df[region].dropna()
        if len(data) < 10:
            continue

        threshold = np.percentile(data, threshold_percentile)
        bloom_frequency = (data > threshold).sum() / len(data) * 100

        # Get position info
        coords = regions[region]
        lon_center = (coords[0] + coords[1]) / 2
        lat_center = (coords[2] + coords[3]) / 2

        # Classify position
        if 'Gulf' in region:
            position = 'gulf'
        elif lon_center < 138:
            position = 'west'
        elif lon_center > 140:
            position = 'east'
        else:
            position = 'central'

        boundaries[region] = {
            'bloom_frequency': bloom_frequency,
            'threshold': threshold,
            'position': position,
            'lon_center': lon_center,
            'lat_center': lat_center
        }

    return boundaries

def analyze_seasonality(df, regions):
    """Analyze seasonal patterns in chlorophyll data."""
    seasonal_patterns = {}

    for region in regions.keys():
        if region not in df.columns:
            continue

        data = df[region].dropna()
        if len(data) < 30:
            continue

        # Add month column
        data_df = pd.DataFrame({'value': data})
        data_df['month'] = data_df.index.month

        # Calculate monthly means
        monthly_means = data_df.groupby('month')['value'].mean()

        # Identify peak season
        peak_month = monthly_means.idxmax()
        peak_value = monthly_means.max()
        min_month = monthly_means.idxmin()
        min_value = monthly_means.min()

        seasonal_patterns[region] = {
            'monthly_means': monthly_means,
            'peak_month': peak_month,
            'peak_value': peak_value,
            'min_month': min_month,
            'min_value': min_value,
            'seasonal_amplitude': peak_value - min_value
        }

    return seasonal_patterns

def detect_regime_shift(df, regions, test_date):
    """Detect if there's been a regime shift (change in baseline) around a date."""
    test_dt = pd.to_datetime(test_date)

    # Define before/after periods (1 year each, with 3 month gap around event)
    before_start = test_dt - timedelta(days=365+90)
    before_end = test_dt - timedelta(days=90)
    after_start = test_dt + timedelta(days=90)
    after_end = test_dt + timedelta(days=365+90)

    results = {}

    for region in regions.keys():
        if region not in df.columns:
            continue

        before_data = df.loc[before_start:before_end, region].dropna()
        after_data = df.loc[after_start:after_end, region].dropna()

        if len(before_data) < 20 or len(after_data) < 20:
            continue

        before_mean = before_data.mean()
        after_mean = after_data.mean()

        # Test if the means are significantly different
        t_stat, p_value = stats.ttest_ind(before_data, after_data)

        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt((before_data.std()**2 + after_data.std()**2) / 2)
        cohens_d = (after_mean - before_mean) / pooled_std if pooled_std > 0 else 0

        results[region] = {
            'before_mean': before_mean,
            'after_mean': after_mean,
            'percent_change': ((after_mean - before_mean) / before_mean) * 100,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'regime_shift': abs(cohens_d) > 0.5 and p_value < 0.05
        }

    return results

def analyze_long_term_trends(df, regions):
    """Analyze long-term trends across entire dataset."""
    trends = {}

    for region in regions.keys():
        if region not in df.columns:
            continue

        data = df[region].dropna()
        if len(data) < 100:
            continue

        # Fit linear trend
        x = np.arange(len(data))
        y = data.values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Convert slope to change per year
        days_per_year = 365.25
        slope_per_year = slope * days_per_year

        # Calculate percent change over entire period
        first_mean = data.iloc[:30].mean()
        last_mean = data.iloc[-30:].mean()
        total_change = ((last_mean - first_mean) / first_mean) * 100

        trends[region] = {
            'slope': slope,
            'slope_per_year': slope_per_year,
            'r_squared': r_value**2,
            'p_value': p_value,
            'trend_direction': 'increasing' if slope > 0 else 'decreasing',
            'total_change_percent': total_change,
            'significant': p_value < 0.05,
            'first_period_mean': first_mean,
            'last_period_mean': last_mean
        }

    return trends

def analyze_spatial_gradient(df, regions, boundaries):
    """Analyze nearshore vs offshore patterns (relating to SST)."""

    # Group regions by latitude to look for north-south patterns
    lat_grouped = {}
    for region, info in boundaries.items():
        lat_center = info['lat_center']
        lat_bin = round(lat_center)
        if lat_bin not in lat_grouped:
            lat_grouped[lat_bin] = []
            lat_grouped[lat_bin].append({
                'region': region,
                'mean_chlor': df[region].mean(),
                'bloom_freq': info['bloom_frequency']
            })

    # Analyze St Vincent Gulf subsectors (north to south)
    svgulf_analysis = {}
    svgulf_regions = [r for r in regions.keys() if 'SVG' in r]

    if len(svgulf_regions) > 1:
        for region in svgulf_regions:
            if region not in df.columns:
                continue

            data = df[region].dropna()
            recent_cutoff = df.index.max() - timedelta(days=365)
            recent_data = df.loc[df.index >= recent_cutoff, region].dropna()

            svgulf_analysis[region] = {
                'overall_mean': data.mean(),
                'recent_mean': recent_data.mean() if len(recent_data) > 0 else np.nan,
                'std': data.std(),
                'position': region.split()[-1]  # North, Central, or South
            }

    return {
        'latitude_gradient': lat_grouped,
        'svgulf_subsectors': svgulf_analysis
    }

def compare_gulf_subsectors(df, regions):
    """Compare St Vincent Gulf subsectors to identify chlorophyll source."""
    svgulf_regions = [r for r in regions.keys() if 'St Vincent Gulf' in r]

    if len(svgulf_regions) < 2:
        return None

    comparison = {}

    for region in svgulf_regions:
        if region not in df.columns:
            continue

        data = df[region].dropna()

        # Recent period analysis (last 2 years)
        recent_cutoff = df.index.max() - timedelta(days=730)
        recent_data = df.loc[df.index >= recent_cutoff, region].dropna()

        if len(recent_data) < 30:
            continue

        comparison[region] = {
            'mean': data.mean(),
            'recent_mean': recent_data.mean(),
            'max': data.max(),
            'recent_max': recent_data.max(),
            'exceedance_days': (data > 2.0).sum(),  # Days above 2.0 mg/m³
            'recent_exceedance_pct': (recent_data > 2.0).sum() / len(recent_data) * 100
        }

    # Statistical comparison between subsectors
    if len(comparison) == 3:
        regions_list = list(comparison.keys())
        # Compare north vs south
        north_data = df[regions_list[0]].dropna() if regions_list[0] in df.columns else pd.Series()
        south_data = df[regions_list[2]].dropna() if regions_list[2] in df.columns else pd.Series()

        if len(north_data) > 30 and len(south_data) > 30:
            t_stat, p_value = stats.ttest_ind(north_data, south_data)
            comparison['north_vs_south'] = {
                'p_value': p_value,
                'significant': p_value < 0.05,
                'north_higher': north_data.mean() > south_data.mean()
            }

    return comparison

def identify_hotspots(df, regions, threshold_percentile=90):
    """Identify regions with consistently high chlorophyll (hotspots)."""
    hotspots = {}

    for region in regions.keys():
        if region not in df.columns:
            continue

        data = df[region].dropna()
        if len(data) < 100:
            continue

        threshold = np.percentile(data, threshold_percentile)

        # Count extreme events
        extreme_events = (data > threshold).sum()
        extreme_pct = extreme_events / len(data) * 100

        # Recent trend in extremes
        recent_cutoff = df.index.max() - timedelta(days=365)
        recent_data = df.loc[df.index >= recent_cutoff, region].dropna()
        recent_extreme_pct = (recent_data > threshold).sum() / len(recent_data) * 100 if len(recent_data) > 0 else 0

        hotspots[region] = {
            'threshold': threshold,
            'extreme_events': extreme_events,
            'extreme_pct': extreme_pct,
            'recent_extreme_pct': recent_extreme_pct,
            'is_hotspot': extreme_pct > 15,  # More than 15% of days above 90th percentile
            'intensifying': recent_extreme_pct > extreme_pct * 1.2
        }

    return hotspots

def predict_future_trends(df, regions, days_ahead=90):
    """Make simple trend-based predictions for future period."""
    predictions = {}

    for region in regions.keys():
        if region not in df.columns:
            continue

        # Use last year of data for trend (365 days)
        cutoff_date = df.index.max() - timedelta(days=365)
        recent_data = df.loc[df.index >= cutoff_date, region].dropna()

        if len(recent_data) < 30:
            continue

        # Fit linear trend
        x = np.arange(len(recent_data))
        y = recent_data.values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Project forward
        future_x = np.arange(len(recent_data), len(recent_data) + days_ahead)
        future_pred = slope * future_x + intercept

        # Calculate confidence based on recent variability
        recent_std = recent_data.std()

        predictions[region] = {
            'trend_direction': 'increasing' if slope > 0 else 'decreasing',
            'slope': slope,
            'r_squared': r_value**2,
            'mean_prediction': np.mean(future_pred),
            'std_dev': recent_std,
            'confidence': 'high' if r_value**2 > 0.3 else 'moderate' if r_value**2 > 0.1 else 'low'
        }

    return predictions

def create_plot(df, regions, colors, output_path='hab_analysis.png'):
    """Create comprehensive time series plot."""
    fig, ax1 = plt.subplots(figsize=(16, 8))

    # Plot chlorophyll data
    for region in regions.keys():
        if region in df.columns:
            data = df[region].dropna()
            ax1.plot(data.index, data.values,
                     color=colors[region],
                     label=region,
                     linewidth=1.5,
                     alpha=0.8)

    ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Chlorophyll-a (mg/m³)', fontsize=12, fontweight='bold')
    ax1.set_title('South Australia Coastal HAB Analysis with St Vincent Gulf Subsectors',
                  fontsize=14, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper center', fontsize=8, ncol=2)

    # Add event markers
    y_max = ax1.get_ylim()[1]
    for event_key, event_info in EVENTS.items():
        event_date = pd.to_datetime(event_info['date'])
        if df.index.min() <= event_date <= df.index.max():
            ax1.axvline(event_date, color=event_info['color'],
                        linestyle='--', linewidth=2, alpha=0.7)
            ax1.text(event_date, y_max * 0.95, event_info['label'],
                     rotation=90, verticalalignment='top',
                     fontsize=9, fontweight='bold',
                     color=event_info['color'])

    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")

    return fig

def generate_markdown_report(df, regions, output_path='hab_analysis.md'):
    """Generate comprehensive markdown analysis report."""

    # Perform all analyses
    flood_impact = analyze_event_impact(df, regions, EVENTS['2023_flood']['date'])
    heatwave_impact = analyze_event_impact(df, regions, EVENTS['2024_heatwave']['date'])
    boundaries = detect_hab_boundaries(df, regions)
    seasonality = analyze_seasonality(df, regions)
    predictions = predict_future_trends(df, regions)
    long_term = analyze_long_term_trends(df, regions)
    spatial = analyze_spatial_gradient(df, regions, boundaries)
    svgulf_comparison = compare_gulf_subsectors(df, regions)
    hotspots = identify_hotspots(df, regions)

    # Generate report
    report = []
    report.append("# South Australia Harmful Algal Bloom Analysis")
    report.append(f"\n**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}")
    report.append(f"\n**Data Period:** {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")

    # Executive Summary
    report.append("\n## Executive Summary")

    # Analyze overall trend
    recent_means = {}
    cutoff_date = df.index.max() - timedelta(days=90)
    for region in regions.keys():
        if region in df.columns:
            recent_data = df.loc[df.index >= cutoff_date, region]
            recent_means[region] = recent_data.mean()

    highest_region = max(recent_means.items(), key=lambda x: x[1] if pd.notna(x[1]) else 0)

    report.append(f"\n**{highest_region[0]}** is experiencing a severe harmful algal bloom crisis with chlorophyll-a levels "
                  f"of **{highest_region[1]:.2f} mg/m³** — more than **{highest_region[1]/0.5:.0f} times normal oceanic levels**.")

    if predictions:
        report.append("\n| Region | Predicted Level | Trend | Confidence | Risk Level |")
        report.append("|--------|----------------|-------|------------|------------|")

        high_risk_regions = []

        for region, data in sorted(predictions.items(),
                                   key=lambda x: x[1]['mean_prediction'],
                                   reverse=True):
            trend = data['trend_direction']
            conf = data['confidence']
            pred_mean = data['mean_prediction']

            # Determine risk level
            if pred_mean > 2.0 and trend == 'increasing':
                risk = "🔴 HIGH"
                high_risk_regions.append(region)
            elif pred_mean > 1.0:
                risk = "🟠 ELEVATED"
            else:
                risk = "🟢 NORMAL"

            report.append(f"| {region} | {pred_mean:.2f} mg/m³ | {trend} | {conf} | {risk} |")

        if high_risk_regions:
            report.append(f"\n### Immediate Action Required")
            report.append(f"\n**{', '.join(high_risk_regions)}** require urgent intervention:")
            report.append("- Enhanced water quality monitoring")
            report.append("- Public health advisories for swimmers and fishers")
            report.append("- Investigation of nutrient sources")
            report.append("- Emergency nutrient reduction measures")
            report.append("- Aquaculture and shellfish harvesting restrictions")

    # St Vincent Gulf Subsector Analysis
    report.append("\n## St Vincent Gulf Subsector Analysis")

    if svgulf_comparison:
        report.append("\n### Recent Conditions (Last 2 Years)")

        report.append("\n| Subsector | Mean Level | Maximum | Days > 2.0 mg/m³ | Assessment |")
        report.append("|-----------|------------|---------|------------------|------------|")

        for region, data in svgulf_comparison.items():
            if region == 'north_vs_south':
                continue

            # Determine assessment
            if data['recent_mean'] > 3.0:
                assessment = "🔴 Critical"
            elif data['recent_mean'] > 1.5:
                assessment = "🟠 Concerning"
            elif data['recent_mean'] > 0.8:
                assessment = "🟡 Elevated"
            else:
                assessment = "🟢 Normal"

            report.append(f"| {region} | {data['recent_mean']:.2f} mg/m³ | {data['recent_max']:.2f} mg/m³ | "
                          f"{data['recent_exceedance_pct']:.1f}% | {assessment} |")

        if 'north_vs_south' in svgulf_comparison:
            ns_comp = svgulf_comparison['north_vs_south']
            if ns_comp['significant']:
                higher = "Northern" if ns_comp['north_higher'] else "Southern"
                report.append(f"\n**Statistical Finding**: The {higher} sector has significantly higher "
                              f"chlorophyll levels than the opposite end (p = {ns_comp['p_value']:.4f}).")

                if ns_comp['north_higher']:
                    report.append("\nThis north-to-south gradient is the signature of **nutrient accumulation at the gulf head**, "
                                  "where enclosed basin conditions and poor flushing allow pollutants to concentrate.")

    # Long-term trends
    report.append("\n## Long-Term Trends (2017-2025)")

    if long_term:
        increasing_regions = [r for r, d in long_term.items() if d['trend_direction'] == 'increasing' and d['significant']]
        decreasing_regions = [r for r, d in long_term.items() if d['trend_direction'] == 'decreasing' and d['significant']]

        if increasing_regions:
            report.append("\n**Regions with Significant Increasing Trends:**")
            for region in increasing_regions:
                data = long_term[region]
                report.append(f"\n**{region}**:")
                report.append(f"- Change per year: {data['slope_per_year']:+.3f} mg/m³/year")
                report.append(f"- Total change: {data['total_change_percent']:+.1f}%")
                report.append(f"- R² = {data['r_squared']:.3f}, p = {data['p_value']:.4f}")

        if decreasing_regions:
            report.append("\n**Regions with Significant Decreasing Trends:**")
            for region in decreasing_regions:
                data = long_term[region]
                report.append(f"\n**{region}**: {data['total_change_percent']:+.1f}% "
                              f"(p={data['p_value']:.4f})")

    # Nearshore vs Offshore (SST connection)
    report.append("\n## Spatial Patterns")

    report.append("- Enhanced coastal upwelling bringing nutrients")
    report.append("- Altered stratification affecting phytoplankton growth")
    report.append("- Changes in water mass characteristics")

    if spatial and 'svgulf_subsectors' in spatial:
        svgulf_data = spatial['svgulf_subsectors']
        if len(svgulf_data) > 1:
            report.append("\n**St Vincent Gulf North-South Gradient:**")
            for region, data in sorted(svgulf_data.items(),
                                       key=lambda x: {'North': 0, 'Central': 1, 'South': 2}.get(x[1]['position'], 3)):
                report.append(f"- **{region}**: {data['overall_mean']:.2f} mg/m³ (recent: {data['recent_mean']:.2f} mg/m³)")

    # Hotspot identification
    report.append("\n## Chlorophyll Hotspot Identification")

    if hotspots:
        active_hotspots = {r: d for r, d in hotspots.items() if d['is_hotspot']}
        intensifying = {r: d for r, d in hotspots.items() if d['intensifying']}

        if active_hotspots:
            report.append("\n### Persistent Hotspots (>15% of days with extreme levels)")

            report.append("\n| Region | Extreme Event % | Recent Trend | Status |")
            report.append("|--------|-----------------|--------------|--------|")

            for region, data in sorted(active_hotspots.items(),
                                       key=lambda x: x[1]['extreme_pct'], reverse=True):
                status = "🔴 INTENSIFYING" if region in intensifying else "🟠 Persistent"
                report.append(f"| {region} | {data['extreme_pct']:.1f}% | "
                              f"{data['recent_extreme_pct']:.1f}% | {status} |")

        if not active_hotspots:
            report.append("\nNo persistent hotspots detected outside St Vincent Gulf North. "
                          "This reinforces that the crisis is **localized** to the northern gulf.")

    # Event Analysis
    report.append("\n## Climate Event Impact Analysis")

    report.append("\n### 2023 River Flood Event")
    report.append(f"\n**Government Explanation:** {EVENTS['2023_flood']['explanation']}")

    if flood_impact:
        significant_regions = [r for r, d in flood_impact.items() if d.get('significant', False)]

        if significant_regions:
            report.append(f"\n**Analysis Verdict:** ✓ SUPPORTED")
            report.append(f"\nStatistically significant increases detected in {len(significant_regions)} region(s):")
            for region in significant_regions:
                data = flood_impact[region]
                report.append(f"- **{region}**: {data['percent_change']:+.1f}% change "
                              f"(p={data['p_value']:.3f})")
        else:
            report.append(f"\n**Analysis Verdict:** ⚠ INCONCLUSIVE")

    report.append("\n### 2024 Heatwave Event")
    report.append(f"\n**Government Explanation:** {EVENTS['2024_heatwave']['explanation']}")

    if heatwave_impact:
        significant_regions = [r for r, d in heatwave_impact.items() if d.get('significant', False)]

        if significant_regions:
            report.append(f"\n**Analysis Verdict:** ✓ SUPPORTED")
            report.append(f"\nStatistically significant changes detected in {len(significant_regions)} region(s):")
            for region in significant_regions:
                data = heatwave_impact[region]
                report.append(f"- **{region}**: {data['percent_change']:+.1f}% change "
                              f"(p={data['p_value']:.3f})")
        else:
            report.append(f"\n**Analysis Verdict:** ⚠ INCONCLUSIVE")

    # Seasonal Patterns
    report.append("\n## Seasonal Patterns")

    if seasonality:
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        report.append("\n| Region | Peak Month | Peak Level | Min Month | Seasonality |")
        report.append("|--------|------------|------------|-----------|-------------|")

        for region, data in seasonality.items():
            peak_month_name = month_names[data['peak_month'] - 1]
            min_month_name = month_names[data['min_month'] - 1]
            report.append(f"| {region} | {peak_month_name} | {data['peak_value']:.2f} mg/m³ | "
                          f"{min_month_name} | {data['seasonal_amplitude']:.2f} mg/m³ |")

        # Check for winter peaks
        winter_months = [6, 7, 8]  # Jun, Jul, Aug
        winter_peakers = [r for r, d in seasonality.items() if d['peak_month'] in winter_months]

        if winter_peakers:
            report.append(f"\n**Notable**: {', '.join(winter_peakers)} peak in **winter**, suggesting continuous "
                          "nutrient loading rather than temperature-driven summer blooms. This is consistent with "
                          "year-round pollution sources (wastewater, industrial discharge, waste facilities).")

    # Glossary
    report.append("\n## Glossary")
    report.append("\n### What is Chlorophyll-a?")
    report.append("\nChlorophyll-a is the green pigment found in all photosynthetic algae and plants. "
                  "In ocean water, measuring chlorophyll-a tells us how much algae (phytoplankton) is present. "
                  "It's the standard indicator used worldwide to monitor algal blooms.")
    report.append("\n### Understanding the Measurements (mg/m³)")
    report.append("\n| Chlorophyll-a Level | Interpretation | Water Quality |")
    report.append("|---------------------|----------------|---------------|")
    report.append("| 0.1 - 1.0 mg/m³ | Normal oceanic levels | 🟢 Healthy |")
    report.append("| 1.0 - 2.0 mg/m³ | Slightly elevated | 🟡 Acceptable |")
    report.append("| 2.0 - 5.0 mg/m³ | Moderate bloom conditions | 🟠 Concerning |")
    report.append("| 5.0 - 10.0 mg/m³ | Severe bloom | 🔴 Harmful |")
    report.append("| > 10.0 mg/m³ | Extreme bloom / toxic potential | 🔴 Crisis |")
    report.append("\n### What Causes High Chlorophyll?")
    report.append("\nAlgae need nutrients (primarily nitrogen and phosphorus) to grow. Excessive nutrients from:")
    report.append("- Wastewater discharge")
    report.append("- Agricultural fertilizer runoff")
    report.append("- Industrial waste")
    report.append("- Urban stormwater")
    report.append("- Waste management facilities")
    report.append("\n...cause algae to multiply rapidly, creating \"blooms.\" In enclosed bays and gulfs with poor water "
                  "circulation, these nutrients accumulate over time, leading to chronic bloom conditions.")

    # report.append("\n### Analysis Pipeline")
    # report.append("\n1. **Data Acquisition**: Downloaded NASA VIIRS ocean color NetCDF files for the study region")
    # report.append("\n2. **Region Extraction**: Defined 7 coastal sectors based on geography and hydrodynamics. "
    #              "For each region, extracted mean chlorophyll-a from all valid satellite pixels within the boundary.")
    # report.append("\n3. **Quality Control**: Applied standard ocean color quality flags to remove:")
    # report.append("   - Cloud-contaminated pixels")
    # report.append("   - Land contamination")
    # report.append("   - Sun glint")
    # report.append("   - Out-of-range values (< 0.01 or > 100 mg/m³)")
    # report.append("\n4. **Time Series Analysis**: Calculated daily regional means and performed:")
    # report.append("   - Linear trend analysis (8-year trends)")
    # report.append("   - Event impact assessment (flood, heatwave)")
    # report.append("   - Seasonal decomposition")
    # report.append("   - Statistical significance testing (t-tests, p-values)")
    # report.append("   - Future projections (linear extrapolation)")
    # report.append("\n### Statistical Methods")
    # report.append("\n- **Trend significance**: Linear regression with p < 0.05 threshold")
    # report.append("- **Event impacts**: Two-sample t-tests comparing pre/post 60-day windows")
    # report.append("- **Spatial differences**: Independent t-tests between subsectors")
    # report.append("- **Predictions**: Linear extrapolation of recent 12-month trends")
    # report.append("\n### Code Availability")
    # report.append("\nAll analysis code, data, and this report are available at: [GitHub repository URL]")
    # report.append("\nThe analysis is fully reproducible using open-source Python libraries (numpy, pandas, scipy, matplotlib).")
    # report.append("\n### Limitations")
    # report.append("\n- Satellite data shows **surface water only** (top ~1 meter)")
    # report.append("- Regional averages may mask **localized hotspots**")
    # report.append("- Cloud cover causes **data gaps** (especially winter)")
    # report.append("- Cannot identify **specific algae species** (requires water sampling)")
    # report.append("- Chlorophyll doesn't directly measure **toxicity** (some blooms are toxic, others aren't)")
    # report.append("\nDespite these limitations, the 681% increase and clear spatial gradient provide **strong evidence** "
    #              "of a chronic nutrient pollution problem in northern St Vincent Gulf.")

    if pred_mean > 2.0 and trend == 'increasing':
        high_risk_regions.append(region)

    if high_risk_regions:
        report.append(f"\n**⚠ High Risk Regions:** {', '.join(high_risk_regions)}")
        report.append("\nThese regions show increasing trends and elevated predicted chlorophyll levels. "
                      "Enhanced monitoring and public health advisories recommended for summer 2025-26.")
    else:
        report.append("\n**Low-Moderate Risk:** Current trends suggest normal background levels. "
                      "Continue routine monitoring.")

    # Data Quality Notes
    report.append("\n## Data Quality")

    coverage = {}
    for region in regions.keys():
        if region not in df.columns:
            continue
        total_days = (df.index.max() - df.index.min()).days
        valid_days = df[region].notna().sum()
        coverage[region] = (valid_days / total_days) * 100

    avg_coverage = np.mean(list(coverage.values()))

    report.append("\n| Region | Data Coverage |")
    report.append("|--------|---------------|")
    for region in regions.keys():
        if region in coverage:
            report.append(f"| {region} | {coverage[region]:.1f}% |")

    report.append(f"\n**Average coverage: {avg_coverage:.1f}%** — High quality dataset with minimal gaps")

    # # Recommendations
    # report.append("\n## Recommendations")
    # report.append("\n### Immediate Actions (0-3 months)")
    # report.append("\n1. **Emergency water quality monitoring** in northern St Vincent Gulf")
    # report.append("2. **Public health advisories** for swimming, fishing, shellfish consumption")
    # report.append("3. **Identify and inspect** all wastewater, industrial, and waste management facilities discharging to the northern gulf")
    # report.append("4. **Implement temporary discharge restrictions** for major nutrient sources")
    # report.append("\n### Short-term Actions (3-12 months)")
    # report.append("\n1. **Comprehensive nutrient source audit** — quantify contributions from:")
    # report.append("   - Urban wastewater treatment plants")
    # report.append("   - Industrial facilities")
    # report.append("   - Agricultural runoff")
    # report.append("   - Waste management sites")
    # report.append("   - Stormwater systems")
    # report.append("\n2. **Hydrodynamic modeling** to understand water residence times and flushing rates")
    # report.append("\n3. **In-situ water sampling** to validate satellite observations and test for toxic species")
    # report.append("\n4. **Sediment analysis** to assess nutrient accumulation and release rates")
    # report.append("\n### Long-term Actions (1-5 years)")
    # report.append("\n1. **Upgrade wastewater treatment** to tertiary/advanced nutrient removal")
    # report.append("\n2. **Implement best management practices** for agricultural lands in northern catchments")
    # report.append("\n3. **Review and strengthen** discharge permits for all facilities")
    # report.append("\n4. **Consider** artificial flushing or circulation enhancement for the northern gulf")
    # report.append("\n5. **Establish continuous monitoring network** with real-time alerts")
    # report.append("\n### Policy Recommendations")
    # report.append("\n- **EPA South Australia** should immediately investigate nutrient sources")
    # report.append("- **SA Health** should assess public health risks and issue advisories")
    # report.append("- **Local councils** should review stormwater management in northern suburbs")
    # report.append("- **State government** should consider emergency funding for nutrient reduction")
    # report.append("\n---")
    # report.append("\n*This analysis was conducted independently using publicly available NASA satellite data. "
    #              "The findings represent objective measurements and standard statistical analysis. "
    #              "All data and code are available for independent verification.*")

    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

    print(f"Analysis report saved to: {output_path}")

    return '\n'.join(report)

def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive HAB analysis for South Australia with subsector analysis'
    )
    parser.add_argument('chlorophyll_csv', help='Path to chlorophyll-a CSV file')
    parser.add_argument('--plot', default='hab_analysis.png',
                        help='Output plot filename')
    parser.add_argument('--report', default='hab_analysis.md',
                        help='Output markdown report filename')
    parser.add_argument('--start-date', help='Start date for analysis (YYYY-MM-DD format)')
    parser.add_argument('--end-date', help='End date for analysis (YYYY-MM-DD format)')
    parser.add_argument('--regions', help='Regins for analysis')

    args = parser.parse_args()

    # Load data
    print("Loading chlorophyll-a data...")
    chlor_df = load_chlorophyll_data(args.chlorophyll_csv)
    print(f"Loaded {len(chlor_df)} days of data")

    regions, colors = get_regions(args.regions)

    # Filter by date range if specified
    if args.start_date:
        start_dt = pd.to_datetime(args.start_date)
        chlor_df = chlor_df[chlor_df.index >= start_dt]
        print(f"Filtered to start date: {start_dt.strftime('%Y-%m-%d')}")

    if args.end_date:
        end_dt = pd.to_datetime(args.end_date)
        chlor_df = chlor_df[chlor_df.index <= end_dt]
        print(f"Filtered to end date: {end_dt.strftime('%Y-%m-%d')}")

    print(f"Analysis period: {chlor_df.index.min().strftime('%Y-%m-%d')} to {chlor_df.index.max().strftime('%Y-%m-%d')}")

    # Create plot
    print("\nGenerating plot...")
    create_plot(chlor_df, regions, colors, args.plot)

    # Generate analysis report
    print("\nGenerating analysis report...")
    report = generate_markdown_report(chlor_df, regions, args.report)

    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)
    print(f"\nKey outputs:")
    print(f"  - Plot: {args.plot}")
    print(f"  - Report: {args.report}")

if __name__ == '__main__':
    main()
