#!/usr/bin/env python3
"""
Comprehensive Ocean Thermal Energy Analysis with Marine Heat Wave Detection
Calculates energy trends, integrated energy, degree-days, and identifies marine heat waves
"""
# python energy_analysis.py sst_data.csv
# With custom parameters
# python energy_analysis.py sst_data.csv --depth 15 --baseline 16 --output my_results.csv
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
from scipy import stats
from scipy.integrate import trapezoid
from viirs_regions import get_regions
warnings.filterwarnings('ignore')


def calculate_comprehensive_energy_analysis(df, regions, depth=10,
                                            grid_cell_area_km2=0.5625,
                                            baseline_temp=15.0):
    """
    Calculate comprehensive ocean thermal energy metrics for each region.

    Parameters:
    -----------
    df : DataFrame
        Must have 'date' column and SST columns for each region (format: 'Region_sst')
    regions : list
        List of region names. If None, auto-detect from columns ending in '_sst'
    depth : float
        Mixed layer depth in meters (default 10m for SST measurement)
    grid_cell_area_km2 : float
        Area of grid cell in km² (VIIRS ~0.75km × 0.75km = 0.5625 km²)
    baseline_temp : float
        Reference temperature for anomaly calculations (default 15°C)

    Returns:
    --------
    DataFrame with comprehensive energy metrics for each region
    """
    # Constants
    RHO = 1025  # kg/m³ - seawater density
    CP = 3850   # J/(kg·°C) - specific heat capacity of seawater

    print(f"## Ocean temperature analysis")
    print(f"")
    print(f"- Water depth measured: {depth} m")
    print(f"- Sampling area per cell: {grid_cell_area_km2} km²")
    print(f"- Reference temperature: {baseline_temp}°C")

    results = []

    for region in regions:
        sst_col = f"{region}"

        if sst_col not in df.columns:
            print(f"\n> **Warning:** {region} — data column not found, skipping.")
            continue

        # Get clean data
        clean_data = df[['date', sst_col]].dropna().copy()

        if len(clean_data) < 10:
            print(f"\n> **Warning:** {region} — not enough data "
                  f"({len(clean_data)} points), skipping.")
            continue

        # ================================================================
        # SETUP CALCULATIONS
        # ================================================================
        volume_per_m2 = depth  # m³/m²
        mass_per_m2 = RHO * volume_per_m2  # kg/m²
        area_m2 = grid_cell_area_km2 * 1e6  # m²

        # Thermal energy content (relative to 0°C) in MJ/m²
        clean_data['thermal_energy'] = (
            mass_per_m2 * CP * clean_data[sst_col] / 1e6
        )

        # Anomaly energy (relative to baseline)
        clean_data['temp_anomaly'] = clean_data[sst_col] - baseline_temp
        clean_data['anomaly_energy'] = (
            mass_per_m2 * CP * clean_data['temp_anomaly'] / 1e6
        )

        # Time calculations
        clean_data['year'] = clean_data['date'].dt.year
        clean_data['quarter'] = clean_data['date'].dt.quarter
        start_date = clean_data['date'].min()
        end_date = clean_data['date'].max()
        time_span_years = (end_date - start_date).days / 365.25

        # Convert dates to numeric for regression
        x_days = (clean_data['date'] - start_date).dt.days.values
        y_sst = clean_data[sst_col].values
        y_energy = clean_data['thermal_energy'].values

        # ================================================================
        # 1. LINEAR TRENDS (Temperature and Energy)
        # ================================================================
        # SST trend
        slope_sst, intercept_sst, r_sst, p_sst, stderr_sst = stats.linregress(x_days, y_sst)
        sst_trend_per_year = slope_sst * 365.25  # °C/year
        sst_confidence_95 = 1.96 * stderr_sst * 365.25

        # Energy trend
        slope_energy, intercept_energy, r_energy, p_energy, stderr_energy = stats.linregress(x_days, y_energy)
        energy_trend_per_year = slope_energy * 365.25  # MJ/m²/year

        # Power trend (W/m²)
        power_trend_W_per_m2_per_day = slope_energy * 1e6 / (24 * 3600)
        power_trend_mW_per_m2_per_year = power_trend_W_per_m2_per_day * 365.25 * 1000

        # ================================================================
        # 2. INTEGRATED ENERGY (Area Under Curve)
        # ================================================================
        total_integrated_energy = trapezoid(y_energy, x_days)  # MJ·days/m²
        annual_integrated_energy = total_integrated_energy / time_span_years

        # Anomaly integrated energy
        y_anomaly = clean_data['anomaly_energy'].values
        total_anomaly_energy = trapezoid(y_anomaly, x_days)
        annual_anomaly_energy = total_anomaly_energy / time_span_years

        # ================================================================
        # 3. DEGREE-DAYS
        # ================================================================
        heating_dd = clean_data[clean_data['temp_anomaly'] > 0]['temp_anomaly'].sum()
        cooling_dd = abs(clean_data[clean_data['temp_anomaly'] < 0]['temp_anomaly'].sum())
        net_dd = heating_dd - cooling_dd

        heating_dd_per_year = heating_dd / time_span_years
        cooling_dd_per_year = cooling_dd / time_span_years
        net_dd_per_year = net_dd / time_span_years

        # ================================================================
        # 4. ENERGY RATE OF CHANGE
        # ================================================================
        clean_data['energy_diff'] = clean_data['thermal_energy'].diff()
        clean_data['days_diff'] = clean_data['date'].diff().dt.days
        clean_data['energy_rate'] = clean_data['energy_diff'] / clean_data['days_diff']

        warming_rates = clean_data[clean_data['energy_rate'] > 0]['energy_rate']
        cooling_rates = clean_data[clean_data['energy_rate'] < 0]['energy_rate']

        mean_warming_rate = warming_rates.mean() if len(warming_rates) > 0 else 0
        mean_cooling_rate = abs(cooling_rates.mean()) if len(cooling_rates) > 0 else 0
        max_warming_rate = warming_rates.max() if len(warming_rates) > 0 else 0
        max_cooling_rate = abs(cooling_rates.min()) if len(cooling_rates) > 0 else 0

        # ================================================================
        # 5. EXTREME EVENTS & MARINE HEAT WAVES
        # ================================================================
        energy_95 = clean_data['thermal_energy'].quantile(0.95)
        energy_90 = clean_data['thermal_energy'].quantile(0.90)
        days_above_95 = (clean_data['thermal_energy'] > energy_95).sum()
        days_above_90 = (clean_data['thermal_energy'] > energy_90).sum()
        pct_extreme = (days_above_95 / len(clean_data)) * 100

        # Marine Heat Wave Detection (90th percentile, 5+ consecutive days)
        sst_90 = clean_data[sst_col].quantile(0.90)
        clean_data['above_90'] = clean_data[sst_col] > sst_90

        # Identify consecutive sequences
        clean_data['event_group'] = (clean_data['above_90'] != clean_data['above_90'].shift()).cumsum()
        mhw_events = clean_data[clean_data['above_90']].groupby('event_group').agg({
            'date': ['first', 'last', 'count'],
            sst_col: ['mean', 'max']
        })

        # Filter for events >= 5 days
        mhw_events = mhw_events[mhw_events[('date', 'count')] >= 5].copy()
        mhw_events.columns = ['start_date', 'end_date', 'duration_days', 'mean_sst', 'max_sst']
        mhw_events['intensity'] = mhw_events['mean_sst'] - sst_90
        mhw_events['max_intensity'] = mhw_events['max_sst'] - sst_90

        num_mhw = len(mhw_events)
        total_mhw_days = mhw_events['duration_days'].sum() if num_mhw > 0 else 0

        # ================================================================
        # 6. SEASONAL PATTERNS
        # ================================================================
        seasonal_means = clean_data.groupby('quarter')['thermal_energy'].mean()
        q1_mean = seasonal_means.get(1, np.nan)  # Summer
        q3_mean = seasonal_means.get(3, np.nan)  # Winter
        seasonal_amplitude = q1_mean - q3_mean if not np.isnan(q1_mean) and not np.isnan(q3_mean) else np.nan

        # ================================================================
        # 7. YEAR-OVER-YEAR CHANGES
        # ================================================================
        yearly_integrated = clean_data.groupby('year').apply(
            lambda x: trapezoid(x['thermal_energy'].values,
                                (x['date'] - x['date'].min()).dt.days.values)
            if len(x) > 1 else 0
        )

        if len(yearly_integrated) >= 3:
            years = yearly_integrated.index.values
            energies = yearly_integrated.values
            slope_yoy, _, r_yoy, p_yoy, _ = stats.linregress(years, energies)
        else:
            slope_yoy = np.nan
            r_yoy = np.nan
            p_yoy = np.nan

        # ================================================================
        # 8. PERSISTENCE (Autocorrelation)
        # ================================================================
        energy_series = pd.Series(clean_data['thermal_energy'].values)
        autocorr_7day = energy_series.autocorr(lag=7) if len(energy_series) > 7 else np.nan

        # ================================================================
        # 9. BASIC STATISTICS
        # ================================================================
        mean_sst = y_sst.mean()
        std_sst = y_sst.std()
        min_sst = y_sst.min()
        max_sst = y_sst.max()

        mean_energy = y_energy.mean()
        std_energy = y_energy.std()

        # ================================================================
        # COMPILE RESULTS
        # ================================================================
        results.append({
            'region': region,

            # Basic statistics
            'mean_sst_C': mean_sst,
            'std_sst_C': std_sst,
            'min_sst_C': min_sst,
            'max_sst_C': max_sst,
            'mean_energy_MJ_m2': mean_energy,
            'std_energy_MJ_m2': std_energy,

            # Linear trends
            'sst_trend_C_yr': sst_trend_per_year,
            'sst_trend_conf95': sst_confidence_95,
            'sst_trend_pvalue': p_sst,
            'sst_trend_r2': r_sst**2,
            'energy_trend_MJ_m2_yr': energy_trend_per_year,
            'power_trend_mW_m2_yr': power_trend_mW_per_m2_per_year,
            'energy_trend_pvalue': p_energy,
            'energy_trend_r2': r_energy**2,

            # Integrated energy (AREA UNDER CURVE)
            'total_integrated_GJ_days_m2': total_integrated_energy / 1000,
            'annual_integrated_GJ_days_m2_yr': annual_integrated_energy / 1000,
            'annual_anomaly_GJ_days_m2_yr': annual_anomaly_energy / 1000,

            # Degree-days
            'heating_dd_yr': heating_dd_per_year,
            'cooling_dd_yr': cooling_dd_per_year,
            'net_dd_yr': net_dd_per_year,

            # Energy change rates
            'mean_warming_rate_MJ_m2_day': mean_warming_rate,
            'mean_cooling_rate_MJ_m2_day': mean_cooling_rate,
            'max_warming_rate_MJ_m2_day': max_warming_rate,
            'max_cooling_rate_MJ_m2_day': max_cooling_rate,

            # Extreme events & Marine Heat Waves
            'days_above_95pct': days_above_95,
            'days_above_90pct': days_above_90,
            'pct_time_extreme': pct_extreme,
            'energy_95pct_MJ_m2': energy_95,
            'num_marine_heatwaves': num_mhw,
            'total_mhw_days': total_mhw_days,
            'sst_90pct_threshold_C': sst_90,

            # Seasonal
            'seasonal_amplitude_MJ_m2': seasonal_amplitude,
            'summer_mean_energy_MJ_m2': q1_mean,
            'winter_mean_energy_MJ_m2': q3_mean,

            # Year-over-year
            'yoy_integrated_trend_GJ_days_m2_yr2': slope_yoy / 1000 if not np.isnan(slope_yoy) else np.nan,
            'yoy_trend_r2': r_yoy**2 if not np.isnan(r_yoy) else np.nan,
            'yoy_trend_pvalue': p_yoy if not np.isnan(p_yoy) else np.nan,

            # Persistence
            'energy_autocorr_7day': autocorr_7day,

            # Metadata
            'data_points': len(clean_data),
            'time_span_years': time_span_years,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })

        # ================================================================
        # PLAIN-LANGUAGE PER-REGION SUMMARY (markdown)
        # ================================================================
        sig_label = "statistically reliable" if p_sst < 0.05 else "not statistically reliable"
        trend_dir = "Warming" if sst_trend_per_year > 0 else "Cooling"

        print(f"\n### {region}")
        print(f"")
        print(f"- **Average temperature:** {mean_sst:.1f}°C "
              f"(range {min_sst:.1f}–{max_sst:.1f}°C)")
        print(f"- **{trend_dir} trend:** {sst_trend_per_year:+.3f}°C per year "
              f"(±{sst_confidence_95:.3f}°C) — {sig_label}")
        print(f"- **Days warmer than normal per year:** {heating_dd_per_year:.0f} &nbsp; "
              f"**Cooler than normal:** {cooling_dd_per_year:.0f}")

        if num_mhw > 0:
            print(f"")
            print(f"**{num_mhw} heat wave{'s' if num_mhw > 1 else ''} detected "
                  f"({int(total_mhw_days)} days total)** "
                  f"— unusually warm threshold: above {sst_90:.1f}°C")
            print(f"")
            for _, event in mhw_events.iterrows():
                start = event['start_date'].strftime('%b %-d %Y')
                end   = event['end_date'].strftime('%b %-d %Y')
                print(f"  - {start} – {end}: **{int(event['duration_days'])} days** · "
                      f"avg {event['mean_sst']:.1f}°C "
                      f"(+{event['intensity']:.1f}°C above threshold) · "
                      f"peak {event['max_sst']:.1f}°C "
                      f"(+{event['max_intensity']:.1f}°C)")
        else:
            print(f"- No heat waves detected "
                  f"(unusually warm threshold: {sst_90:.1f}°C)")

    # Create results DataFrame
    results_df = pd.DataFrame(results)
    print("\n---\n")

    return results_df


def plot_comprehensive_dashboard(df, results_df, output_file='energy_dashboard.png', figsize=(18, 12)):
    """
    Create comprehensive visualization dashboard.
    """
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)

    # Sort by integrated energy
    results_sorted = results_df.sort_values('annual_integrated_GJ_days_m2_yr')

    # Plot 1: Annual Integrated Energy
    ax1 = fig.add_subplot(gs[0, 0])
    colors1 = plt.cm.RdYlBu_r(np.linspace(0.2, 0.8, len(results_sorted)))
    ax1.barh(results_sorted['region'], results_sorted['annual_integrated_GJ_days_m2_yr'],
             color=colors1, alpha=0.8)
    ax1.set_xlabel('Annual heat stored (GJ·days/m²)', fontsize=10)
    ax1.set_title('Heat stored in the water column', fontsize=11, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)

    # Plot 2: SST Trends
    ax2 = fig.add_subplot(gs[0, 1])
    colors2 = ['red' if x > 0 else 'blue' for x in results_sorted['sst_trend_C_yr']]
    ax2.barh(results_sorted['region'], results_sorted['sst_trend_C_yr'],
             color=colors2, alpha=0.7)
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax2.set_xlabel('Temperature change (°C/year)', fontsize=10)
    ax2.set_title('Warming or cooling per year', fontsize=11, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)

    # Add significance markers
    for idx, row in results_sorted.iterrows():
        if row['sst_trend_pvalue'] < 0.05:
            marker = '**' if row['sst_trend_pvalue'] < 0.01 else '*'
            ax2.text(row['sst_trend_C_yr'], row['region'], f' {marker}',
                     ha='left' if row['sst_trend_C_yr'] > 0 else 'right',
                     va='center', fontsize=10, fontweight='bold')

    # Plot 3: Marine Heat Waves
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.barh(results_sorted['region'], results_sorted['num_marine_heatwaves'],
             color='darkred', alpha=0.7)
    ax3.set_xlabel('Number of heat waves', fontsize=10)
    ax3.set_title('Heat waves detected', fontsize=11, fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)

    # Plot 4: Energy Change Rates
    ax4 = fig.add_subplot(gs[1, 0])
    x = np.arange(len(results_sorted))
    width = 0.35
    ax4.bar(x - width/2, results_sorted['mean_warming_rate_MJ_m2_day'], width,
            label='Warming', color='orange', alpha=0.7)
    ax4.bar(x + width/2, results_sorted['mean_cooling_rate_MJ_m2_day'], width,
            label='Cooling', color='cyan', alpha=0.7)
    ax4.set_xticks(x)
    ax4.set_xticklabels(results_sorted['region'], rotation=45, ha='right', fontsize=8)
    ax4.set_ylabel('Rate (MJ/m²/day)', fontsize=10)
    ax4.set_title('How fast the water heats or cools', fontsize=11, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(axis='y', alpha=0.3)

    # Plot 5: MHW Days
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.barh(results_sorted['region'], results_sorted['total_mhw_days'],
             color='orangered', alpha=0.7)
    ax5.set_xlabel('Total days', fontsize=10)
    ax5.set_title('Total days spent in a heat wave', fontsize=11, fontweight='bold')
    ax5.grid(axis='x', alpha=0.3)

    # Plot 6: Seasonal Amplitude
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.barh(results_sorted['region'], results_sorted['seasonal_amplitude_MJ_m2'],
             color='purple', alpha=0.7)
    ax6.set_xlabel('Summer–winter difference (MJ/m²)', fontsize=10)
    ax6.set_title('Summer–winter temperature swing', fontsize=11, fontweight='bold')
    ax6.grid(axis='x', alpha=0.3)

    # Plot 7: Degree-Days
    ax7 = fig.add_subplot(gs[2, 0])
    x = np.arange(len(results_sorted))
    ax7.bar(x - width/2, results_sorted['heating_dd_yr'], width,
            label='Warmer than normal', color='red', alpha=0.7)
    ax7.bar(x + width/2, results_sorted['cooling_dd_yr'], width,
            label='Cooler than normal', color='blue', alpha=0.7)
    ax7.set_xticks(x)
    ax7.set_xticklabels(results_sorted['region'], rotation=45, ha='right', fontsize=8)
    ax7.set_ylabel('Days per year', fontsize=10)
    ax7.set_title('Warmer-than-normal vs cooler-than-normal days', fontsize=11, fontweight='bold')
    ax7.legend(fontsize=9)
    ax7.grid(axis='y', alpha=0.3)

    # Plot 8: Mean Energy vs Mean SST
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.scatter(results_df['mean_sst_C'], results_df['mean_energy_MJ_m2'],
                s=100, alpha=0.6, c=results_df['num_marine_heatwaves'],
                cmap='YlOrRd')
    for idx, row in results_df.iterrows():
        ax8.annotate(row['region'], (row['mean_sst_C'], row['mean_energy_MJ_m2']),
                     fontsize=7, alpha=0.7)
    ax8.set_xlabel('Average temperature (°C)', fontsize=10)
    ax8.set_ylabel('Stored heat (MJ/m²)', fontsize=10)
    ax8.set_title('Average temperature vs stored heat', fontsize=11, fontweight='bold')
    ax8.grid(alpha=0.3)

    # Plot 9: Power Trend
    ax9 = fig.add_subplot(gs[2, 2])
    colors9 = ['red' if x > 0 else 'blue' for x in results_sorted['power_trend_mW_m2_yr']]
    ax9.barh(results_sorted['region'], results_sorted['power_trend_mW_m2_yr'],
             color=colors9, alpha=0.7)
    ax9.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax9.set_xlabel('Heat flux trend (mW/m²/year)', fontsize=10)
    ax9.set_title('Rate of heat gain or loss', fontsize=11, fontweight='bold')
    ax9.grid(axis='x', alpha=0.3)

    fig.suptitle('Ocean Temperature Analysis — Marine Heat Wave Report',
                 fontsize=14, fontweight='bold', y=0.995)
    fig.text(0.5, 0.01,
             '* reliable trend (95% confidence)   ** highly reliable trend (99% confidence)',
             ha='center', fontsize=9, style='italic')

    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    return fig


def export_results(results_df, output_file='energy_analysis_results.csv'):
    """
    Export results to CSV.
    """
    results_df.to_csv(output_file, index=False, float_format='%.6f')


def print_summary(results_df):
    """
    Print plain-language key findings summary in markdown.
    """
    print(f"\n{'='*60}")
    print("## Results summary")
    print(f"{'='*60}\n")

    if len(results_df) == 0:
        print("No results to summarise.")
        return

    # ----------------------------------------------------------------
    # Temperature trends
    # ----------------------------------------------------------------
    if results_df['sst_trend_C_yr'].notna().any():
        max_w = results_df.loc[results_df['sst_trend_C_yr'].idxmax()]
        max_c = results_df.loc[results_df['sst_trend_C_yr'].idxmin()]

        sig_w = "reliable trend" if max_w['sst_trend_pvalue'] < 0.05 else "not statistically reliable"
        sig_c = "reliable trend" if max_c['sst_trend_pvalue'] < 0.05 else "not statistically reliable"

        print("### Temperature change over time\n")
        print(f"- **Warming fastest:** {max_w['region']}")
        print(f"  {max_w['sst_trend_C_yr']:+.3f}°C per year "
              f"(±{max_w['sst_trend_conf95']:.3f}°C) — {sig_w}")
        print(f"- **Cooling fastest:** {max_c['region']}")
        print(f"  {max_c['sst_trend_C_yr']:+.3f}°C per year "
              f"(±{max_c['sst_trend_conf95']:.3f}°C) — {sig_c}")

    # ----------------------------------------------------------------
    # Marine Heat Waves
    # ----------------------------------------------------------------
    if results_df['num_marine_heatwaves'].notna().any():
        total_mhw      = int(results_df['num_marine_heatwaves'].sum())
        total_mhw_days = int(results_df['total_mhw_days'].sum())
        most_mhw       = results_df.loc[results_df['num_marine_heatwaves'].idxmax()]

        print(f"\n### Heat waves\n")
        print(f"> A heat wave is defined as 5 or more consecutive days with temperatures "
              f"above the 90th percentile for that region.\n")
        print(f"- **{total_mhw} heat wave{'s' if total_mhw != 1 else ''} detected** "
              f"across all regions")
        print(f"- **{total_mhw_days} total days** spent in heat wave conditions")
        print(f"- **Most affected area:** {most_mhw['region']} — "
              f"{int(most_mhw['num_marine_heatwaves'])} events, "
              f"{int(most_mhw['total_mhw_days'])} days total")

    # ----------------------------------------------------------------
    # Stored heat (energy accumulation)
    # ----------------------------------------------------------------
    if results_df['annual_integrated_GJ_days_m2_yr'].notna().any():
        max_e = results_df.loc[results_df['annual_integrated_GJ_days_m2_yr'].idxmax()]
        min_e = results_df.loc[results_df['annual_integrated_GJ_days_m2_yr'].idxmin()]

        print(f"\n### Stored heat\n")
        print(f"- **Warmest region:** {max_e['region']} "
              f"({max_e['annual_integrated_GJ_days_m2_yr']:.1f} GJ·days/m²/yr)")
        print(f"- **Coolest region:** {min_e['region']} "
              f"({min_e['annual_integrated_GJ_days_m2_yr']:.1f} GJ·days/m²/yr)")

    print(f"\n{'='*60}\n")


def main():
    """
    Main execution function.
    """
    parser = argparse.ArgumentParser(
        description='VIIRS SST Data - Comprehensive Thermal Energy Analysis with Marine Heat Wave Detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python energy_analysis.py sst_data.csv
  python energy_analysis.py sst_data.csv --depth 15 --baseline 16
        """
    )

    parser.add_argument(
        'sst_filename',
        type=str,
        help='SST data extract CSV file (must have date column and *_sst columns)'
    )

    parser.add_argument(
        '--depth',
        type=float,
        default=10.0,
        help='Mixed layer depth in meters (default: 10.0)'
    )

    parser.add_argument(
        '--baseline',
        type=float,
        default=15.0,
        help='Baseline temperature for anomaly calculations in °C (default: 15.0)'
    )

    parser.add_argument(
        '--grid-area',
        type=float,
        default=0.5625,
        help='Grid cell area in km² (default: 0.5625 for VIIRS ~0.75km resolution)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='energy_analysis_results.csv',
        help='Output CSV filename (default: energy_analysis_results.csv)'
    )

    parser.add_argument(
        '--plot',
        type=str,
        default='energy_dashboard.png',
        help='Output plot filename (default: energy_dashboard.png)'
    )

    parser.add_argument(
        '--regions',
        type=str,
        help='The regions to inspect'
    )

    args = parser.parse_args()

    # Load data
    df = pd.read_csv(args.sst_filename, parse_dates=["date"])
    regions, colors = get_regions(args.regions)

    # Run analysis
    results = calculate_comprehensive_energy_analysis(
        df,
        regions,
        depth=args.depth,
        grid_cell_area_km2=args.grid_area,
        baseline_temp=args.baseline
    )

    # Print summary
    # print_summary(results)
    # Export results
    # export_results(results, args.output)
    # Create visualization
    # plot_comprehensive_dashboard(df, results, args.plot)


if __name__ == "__main__":
    main()
