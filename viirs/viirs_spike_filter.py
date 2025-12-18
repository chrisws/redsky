#!/usr/bin/env python3
"""
Detect and optionally filter suspicious chlorophyll-a spikes.
Identifies single-day extreme values that don't fit the temporal pattern.
"""
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt
from datetime import timedelta

def detect_spikes(df, region, threshold_factor=5.0, window=7):
    """
    Detect suspicious spikes using moving statistics.

    Args:
        df: DataFrame with chlorophyll data
        region: Column name to analyze
        threshold_factor: How many times the rolling std constitutes a spike
        window: Days for rolling window calculation

    Returns:
        DataFrame with spike flags
    """
    data = df[region].copy()

    # Calculate rolling statistics (centered window)
    rolling_mean = data.rolling(window=window, center=True, min_periods=3).mean()
    rolling_std = data.rolling(window=window, center=True, min_periods=3).std()

    # Detect spikes: values that are threshold_factor * std away from local mean
    deviation = np.abs(data - rolling_mean)
    spike_threshold = threshold_factor * rolling_std

    # Flag as spike if:
    # 1. Deviation exceeds threshold
    # 2. Value is much higher than neighbors (not part of sustained bloom)
    is_spike = deviation > spike_threshold

    # Additional check: isolated spikes (not sustained blooms)
    # Look at day before and after
    prev_day = data.shift(1)
    next_day = data.shift(-1)

    # Spike if current value >> both neighbors
    isolated = (data > prev_day * 3) & (data > next_day * 3)

    # Combine criteria: statistical spike AND isolated
    final_spikes = is_spike & isolated & data.notna()

    return final_spikes

def analyze_spikes(csv_path, output_path=None, plot=True):
    """Analyze and optionally filter spikes from chlorophyll data."""

    # Load data
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df = df.set_index('date')

    # Regions to check
    regions = [col for col in df.columns]

    print("="*80)
    print(f"SPIKE DETECTION ANALYSIS")
    print("="*80)

    all_spikes = {}

    for region in regions:
        if region not in df.columns:
            continue

        # Detect spikes
        spikes = detect_spikes(df, region, threshold_factor=5.0, window=7)
        spike_count = spikes.sum()

        if spike_count > 0:
            print(f"\n{region}:")
            print(f"  Total spikes detected: {spike_count}")

            # Show spike details
            spike_dates = df.index[spikes]
            spike_values = df.loc[spikes, region]

            for date, value in zip(spike_dates, spike_values):
                # Get context (day before/after)
                try:
                    prev_val = df.loc[date - timedelta(days=1), region]
                except:
                    prev_val = np.nan

                try:
                    next_val = df.loc[date + timedelta(days=1), region]
                except:
                    next_val = np.nan

                print(f"    {date.strftime('%Y-%m-%d')}: {value:.2f} mg/m³ "
                      f"(prev: {prev_val:.2f}, next: {next_val:.2f})")

            all_spikes[region] = spikes

    # Plot spikes if requested
    if plot and all_spikes:
        n_regions = len(all_spikes)
        fig, axes = plt.subplots(n_regions, 1, figsize=(14, 4*n_regions))

        if n_regions == 1:
            axes = [axes]

        for ax, (region, spikes) in zip(axes, all_spikes.items()):
            # Plot time series
            data = df[region]
            ax.plot(data.index, data.values, 'b-', alpha=0.6, linewidth=1, label='Data')

            # Mark spikes
            spike_dates = df.index[spikes]
            spike_values = df.loc[spikes, region]
            ax.scatter(spike_dates, spike_values, color='red', s=100,
                      marker='x', linewidth=3, label='Detected Spikes', zorder=5)

            # Add rolling mean for reference
            rolling = data.rolling(window=30, center=True).mean()
            ax.plot(rolling.index, rolling.values, 'g--', alpha=0.5,
                   linewidth=2, label='30-day Rolling Mean')

            ax.set_title(f'{region} - Spike Detection', fontweight='bold', fontsize=12)
            ax.set_ylabel('Chlorophyll-a (mg/m³)', fontweight='bold')
            ax.legend(loc='upper left')
            ax.grid(alpha=0.3)

        plt.tight_layout()

        if output_path:
            plot_path = output_path.replace('.csv', '_spike_plot.png')
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"\nSpike plot saved to: {plot_path}")
        else:
            plt.show()

    # Ask user if they want to filter
    print("\n" + "="*80)
    print("FILTERING OPTIONS")
    print("="*80)

    if not all_spikes:
        print("No spikes detected. Data looks clean!")
        return df

    print("\nDo you want to filter these spikes?")
    print("  1. Remove spikes (set to NaN)")
    print("  2. Interpolate spikes (replace with interpolated values)")
    print("  3. Keep all data (no filtering)")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == '1':
        # Remove spikes
        df_filtered = df.copy()
        for region, spikes in all_spikes.items():
            df_filtered.loc[spikes, region] = np.nan
        print("\nSpikes removed (set to NaN)")

    elif choice == '2':
        # Interpolate spikes
        df_filtered = df.copy()
        for region, spikes in all_spikes.items():
            df_filtered.loc[spikes, region] = np.nan
            df_filtered[region] = df_filtered[region].interpolate(method='linear')
        print("\nSpikes interpolated")

    else:
        print("\nNo filtering applied")
        return df

    # Save filtered data
    if output_path:
        # Reset index to get date column back
        df_out = df_filtered.reset_index()
        df_out['date'] = df_out['date'].dt.strftime('%Y%m%d')
        df_out.to_csv(output_path, index=False)
        print(f"\nFiltered data saved to: {output_path}")

    return df_filtered

def quick_check(csv_path, region, max_spikes=20):
    """Quick check for extreme values in a specific region."""
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df = df.set_index('date')

    if region not in df.columns:
        print(f"Region '{region}' not found in data")
        return

    data = df[region].dropna()

    # Show top extreme values
    sorted_data = data.sort_values(ascending=False)

    print(f"\nTop {max_spikes} values for {region}:")
    print("-" * 60)

    for i, (date, value) in enumerate(sorted_data.head(max_spikes).items(), 1):
        # Get neighbors
        try:
            prev_val = df.loc[date - timedelta(days=1), region]
        except:
            prev_val = np.nan

        try:
            next_val = df.loc[date + timedelta(days=1), region]
        except:
            next_val = np.nan

        # Check if isolated spike
        if pd.notna(prev_val) and pd.notna(next_val):
            if value > prev_val * 3 and value > next_val * 3:
                flag = " ⚠️ ISOLATED SPIKE"
            else:
                flag = ""
        else:
            flag = " (no neighbors)"

        print(f"{i:2d}. {date.strftime('%Y-%m-%d')}: {value:6.2f} mg/m³ "
              f"(prev: {prev_val:5.2f}, next: {next_val:5.2f}){flag}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Full analysis:  python spike_filter.py data.csv [filtered_output.csv]")
        print("  Quick check:    python spike_filter.py data.csv --check 'Region Name'")
        sys.exit(1)

    csv_path = sys.argv[1]

    if '--check' in sys.argv:
        region_idx = sys.argv.index('--check') + 1
        if region_idx < len(sys.argv):
            region = sys.argv[region_idx]
            quick_check(csv_path, region)
        else:
            print("Error: Specify region name after --check")
    else:
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        analyze_spikes(csv_path, output_path, plot=True)
