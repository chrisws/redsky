import argparse
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import warnings

from datetime import datetime

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def load_and_prepare_data(filename, start_date, col):
    """Load and prepare data with robust error handling."""

    print(f"📊 Loading data from {filename}...")

    try:
        df = pd.read_csv(filename, parse_dates=["date"])
        print(f"✅ Loaded {len(df)} records")
        print(f"   Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        print("   Make sure you've run the data processing script first!")
        return None
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None

    # Filter by date if specified
    if start_date:
        original_len = len(df)
        df = df[df["date"] >= start_date]
        print(f"   Filtered to {start_date} onwards: {len(df)} records ({original_len - len(df)} excluded)")

    print(f"🔢 Converting to numeric format...")
    if col in df.columns:
        original_valid = df[col].notna().sum() if col in df.columns else 0
        df[col] = pd.to_numeric(df[col], errors="coerce")
        new_valid = df[col].notna().sum()

        if original_valid != new_valid:
            print(f"   ⚠️ {col}: {original_valid - new_valid} values became NaN during conversion")

    # Data quality summary
    print(f"\n📈 Data availability for plotting period:")
    if col in df.columns:
        valid_count = df[col].notna().sum()
        percentage = 100 * valid_count / len(df) if len(df) > 0 else 0
        print(f"   {col:20s}: {valid_count:4d}/{len(df):4d} ({percentage:5.1f}%)")

    return df

def normalize_series(series, method='minmax'):
    """
    Normalize a pandas Series with different methods.

    Parameters:
    - method: 'minmax', 'zscore', or 'robust'
    """
    if series.isna().all():
        return series

    if method == 'minmax':
        # Min-max normalization (0 to 1)
        min_val, max_val = series.min(), series.max()
        if max_val == min_val:  # Handle constant series
            return pd.Series(0.5, index=series.index)
        return (series - min_val) / (max_val - min_val)

    elif method == 'zscore':
        # Z-score normalization (mean=0, std=1)
        return (series - series.mean()) / series.std()

    elif method == 'robust':
        # Robust normalization using median and IQR
        median = series.median()
        q75, q25 = series.quantile(0.75), series.quantile(0.25)
        iqr = q75 - q25
        if iqr == 0:
            return pd.Series(0, index=series.index)
        return (series - median) / iqr

    else:
        raise ValueError("Method must be 'minmax', 'zscore', or 'robust'")

def create_plot(df, col, normalization_method='minmax', figsize=(16, 10),
                fill_gaps=True, max_gap_days=10):
    """Create enhanced multi-axis plot with gap filling and actual value axes."""
    print(f"\n🎨 Creating visualization...")

    # Check which variables we actually have data for
    available_vars = {}
    plot_vars = {
        f"{col}_chlr_a": {'color': 'green', 'style': '-', 'axis': 1, 'label': 'Chlorophyll-a', 'unit': 'mg/m³'},
        f"{col}_sst": {'color': 'red', 'style': '-', 'axis': 2, 'label': 'Sea Surface Temperature', 'unit': '°C'},
    }

    for var in plot_vars:
        if var in df.columns and df[var].notna().sum() > 0:
            available_vars[var] = plot_vars[var]
            print(f"   ✅ {plot_vars[var]['label']}: {df[var].notna().sum()} data points")
        else:
            print(f"   ❌ {plot_vars[var]['label']}: No data available")

    if not available_vars:
        print("❌ No data available for plotting!")
        return None

    # Create figure and axes
    fig, ax1 = plt.subplots(figsize=figsize)
    ax2 = ax1.twinx()

    lines = []
    labels = []

    # Plot each available variable
    for var, props in available_vars.items():
        # Get the original data
        original_data = df[var].copy()

        # Fill gaps if requested
        if fill_gaps:
            filled_data = original_data.copy()
            filled_data = filled_data.interpolate(
                method='linear',
                limit=max_gap_days,
                limit_direction='both'
            )

            filled_count = filled_data.notna().sum() - original_data.notna().sum()
            print(f"   📊 {props['label']}: Filled {filled_count} gap points")
            data_to_plot = filled_data
        else:
            data_to_plot = original_data

        # Choose the appropriate axis
        if props['axis'] == 1:
            ax = ax1
        elif props['axis'] == 2:
            ax = ax2

        # Plot with ACTUAL values (not normalized)
        line, = ax.plot(df["date"], data_to_plot,
                       color=props['color'],
                       linestyle=props['style'],
                       linewidth=2,
                       alpha=0.8,
                       label=f"{props['label']} ({props['unit']})")
        lines.append(line)
        labels.append(f"{props['label']} ({props['unit']})")

        # Add markers for ORIGINAL data points
        data_count = original_data.notna().sum()

        if data_count < 100:
            ax.scatter(df[original_data.notna()]["date"],
                      original_data[original_data.notna()],
                      color=props['color'], s=30, alpha=0.6, zorder=5,
                      edgecolors='white', linewidth=0.5)

    # Formatting
    ax1.set_xlabel("Date", fontsize=12, fontweight='bold')
    ax1.set_ylabel("Chlorophyll-a (mg/m³)", fontsize=12, color='green', fontweight='bold')
    ax2.set_ylabel("Sea Surface Temperature (°C)", fontsize=12, color='red', fontweight='bold')

    # Color the axis ticks to match
    ax1.tick_params(axis='y', labelcolor='green', labelsize=10)
    ax2.tick_params(axis='y', labelcolor='red', labelsize=10)

    # Date formatting
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Grid
    ax1.grid(True, linestyle=":", alpha=0.3, color='gray')

    # Legend
    if fill_gaps:
        legend_title = f"Data (gaps ≤{max_gap_days} days interpolated)"
    else:
        legend_title = "Original data"

    fig.legend(lines, labels,
              loc="upper left",
              bbox_to_anchor=(0.02, 0.98),
              fontsize=11,
              framealpha=0.95,
              title=legend_title,
              title_fontsize=10,
              edgecolor='black')

    # Add title with region name
    region_name = col.replace('_', ' ').title()
    plt.title(f"{region_name}\nChlorophyll-a and Sea Surface Temperature Time Series",
              fontsize=13, pad=15, fontweight='bold')

    # Add horizontal reference lines for chlorophyll thresholds (optional)
    if f"{col}_chlr_a" in available_vars:
        ax1.axhline(y=4.0, color='orange', linestyle='--', alpha=0.5, linewidth=1, label='Elevated (4 mg/m³)')
        ax1.axhline(y=6.0, color='red', linestyle='--', alpha=0.5, linewidth=1, label='Extreme (6 mg/m³)')

    plt.tight_layout()

    return fig, (ax1, ax2)

def main():
    """Main plotting pipeline."""

    parser = argparse.ArgumentParser(
        description='VIIRS data Visualization'
    )
    parser.add_argument(
        'sst_filename',
        type=str,
        help='SST data extract csv'
    )
    parser.add_argument(
        'chlr_a_filename',
        type=str,
        help='CHLR_A data extract csv'
    )
    parser.add_argument(
        'start_date',
        type=str,
        help='Start date'
    )
    parser.add_argument(
        'column_name',
        type=str,
        help='The column to plot'
    )
    parser.add_argument(
        'output_folder',
        type=str,
        help='The column to plot'
    )
    args = parser.parse_args()

    sst_filename = args.sst_filename
    chlr_a_filename = args.chlr_a_filename
    start_date = args.start_date
    col = args.column_name
    output_folder = args.output_folder

    df_sst = load_and_prepare_data(sst_filename, start_date, col)
    if df_sst is None:
        print("❌ Could not load {sst_filename}!")
        return

    df_chl = load_and_prepare_data(chlr_a_filename, start_date, col)
    if df_chl is None:
        print("❌ Could not load {chlr_a_filename}!")
        return

    # new_df = pd.merge(df_sst[['date', col]], df_chl[['date', col]], on='date', how='inner')
    # print(new_df)

    df = df_sst[['date', col]].merge(df_chl[['date', col]], on='date', suffixes=('_sst','_chlr_a'))

    # Create main time series plot
    fig1, axes = create_plot(df, col, normalization_method='minmax')
    if fig1:
        # plt.show()

        # # Save the plot
        filename = col.replace(" ", "").replace("-", "")
        output_filename = f"{output_folder}/viirs_timeseries_{filename}.png"
        fig1.savefig(output_filename, dpi=300, bbox_inches='tight')
        print(f"💾 Main plot saved as: {output_filename}")

    print(f"\n✅ Visualization complete!")

if __name__ == "__main__":
    main()

