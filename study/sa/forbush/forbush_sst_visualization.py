"""
FORBUSH DECREASE - SST CONNECTION VISUALIZATION
================================================
Creates publication-quality figures showing the curious connection between
solar activity (Forbush decreases) and sea surface temperature.

A scientific footnote: Real, statistically significant, but not the main
story of the 2024 algal bloom event.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from datetime import datetime, timedelta
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# ============================================================================
# LOAD DATA
# ============================================================================

def load_all_data(cosmic_ray_csv, sst_csv, forbush_csv):
    """Load cosmic ray, SST, and detected Forbush event data."""
    
    print("Loading data...")
    
    # Cosmic ray data
    cr_df = pd.read_csv(cosmic_ray_csv, names=['Timestamp', 'FractionalDate', 
                                                'UncorrectedCountRate', 
                                                'CorrectedCountRate', 'Pressure'])
    cr_df['date'] = pd.to_datetime(cr_df['Timestamp'], format='ISO8601', errors='coerce', utc=True)
    cr_df = cr_df.dropna(subset=['date'])
    cr_df['date'] = cr_df['date'].dt.tz_localize(None)
    cr_df['cosmic_ray_flux'] = pd.to_numeric(cr_df['CorrectedCountRate'], errors='coerce')
    cr_df = cr_df[['date', 'cosmic_ray_flux']].dropna()
    
    # SST data
    sst_df = pd.read_csv(sst_csv)
    sst_df['date'] = pd.to_datetime(sst_df['date'], format='%Y%m%d')
    sst_long = sst_df.melt(id_vars=['date'], var_name='region', value_name='sst')
    sst_long = sst_long.dropna(subset=['sst'])
    
    # Forbush events
    forbush_df = pd.read_csv(forbush_csv)
    forbush_df['date'] = pd.to_datetime(forbush_df['date'])
    
    print(f"✓ Loaded {len(cr_df)} days of cosmic ray data")
    print(f"✓ Loaded {len(sst_long)} SST observations")
    print(f"✓ Loaded {len(forbush_df)} Forbush events")
    
    return cr_df, sst_long, forbush_df

# ============================================================================
# FIGURE 1: COSMIC RAY TIME SERIES WITH FORBUSH EVENTS
# ============================================================================

def plot_cosmic_ray_timeseries(cr_df, forbush_df, output_path='fig1_cosmic_rays.png'):
    """
    Plot cosmic ray flux over time with Forbush decreases highlighted.
    """
    fig, ax = plt.subplots(figsize=(14, 5))
    
    # Plot cosmic ray flux
    ax.plot(cr_df['date'], cr_df['cosmic_ray_flux'], 
            linewidth=0.5, color='navy', alpha=0.7, label='Cosmic Ray Flux')
    
    # Add 27-day rolling median
    cr_df['baseline'] = cr_df['cosmic_ray_flux'].rolling(window=27, center=True).median()
    ax.plot(cr_df['date'], cr_df['baseline'], 
            linewidth=2, color='orange', alpha=0.8, label='27-day Baseline')
    
    # Highlight Forbush events
    for _, event in forbush_df.iterrows():
        ax.axvline(event['date'], color='red', alpha=0.3, linewidth=1, linestyle='--')
    
    # Add markers for major events
    major_events = forbush_df.nlargest(10, 'magnitude')
    ax.scatter(major_events['date'], 
               [6200] * len(major_events),  # Fixed y position
               s=major_events['magnitude'] * 20,
               color='red', alpha=0.6, zorder=5,
               label='Major Forbush Events')
    
    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel('Count Rate (cts/min)', fontsize=12, fontweight='bold')
    ax.set_title('Cosmic Ray Flux at Oulu Neutron Monitor (2017-2025)\n' + 
                 'Forbush Decreases Highlighted', 
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

# ============================================================================
# FIGURE 2: SST RESPONSE TO FORBUSH EVENTS (COMPOSITE)
# ============================================================================

def plot_composite_sst_response(sst_df, forbush_df, regions_to_plot=None,
                                output_path='fig2_sst_response.png'):
    """
    Create composite plot showing average SST response after Forbush events.
    """
    if regions_to_plot is None:
        regions_to_plot = ['GAB', 'Ceduna', 'Port Lincoln', 'Victor Harbor']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    days_before = 10
    days_after = 40
    
    for idx, region in enumerate(regions_to_plot):
        ax = axes[idx]
        
        region_data = sst_df[sst_df['region'] == region].copy()
        region_data = region_data.sort_values('date')
        
        composite_data = []
        
        for _, fd_event in forbush_df.iterrows():
            fd_date = pd.Timestamp(fd_event['date'])
            
            # Get SST in window around event
            window = region_data[
                (region_data['date'] >= fd_date - pd.Timedelta(days=days_before)) &
                (region_data['date'] <= fd_date + pd.Timedelta(days=days_after))
            ].copy()
            
            if len(window) == 0:
                continue
            
            # Calculate days relative to Forbush event
            window['days_rel'] = (window['date'] - fd_date).dt.days
            
            # Get SST at event (baseline)
            baseline_sst = window[window['days_rel'].abs() <= 1]['sst'].mean()
            
            if np.isnan(baseline_sst):
                continue
            
            # Calculate anomaly
            window['sst_anomaly'] = window['sst'] - baseline_sst
            
            composite_data.append(window[['days_rel', 'sst_anomaly']])
        
        if len(composite_data) == 0:
            continue
        
        # Combine all events
        all_data = pd.concat(composite_data)
        
        # Calculate mean and SEM for each day
        daily_stats = all_data.groupby('days_rel')['sst_anomaly'].agg(['mean', 'sem', 'count'])
        
        # Plot
        ax.plot(daily_stats.index, daily_stats['mean'], 
                linewidth=2, color='darkblue', label='Mean SST Anomaly')
        
        # Add confidence interval
        ax.fill_between(daily_stats.index,
                        daily_stats['mean'] - 1.96 * daily_stats['sem'],
                        daily_stats['mean'] + 1.96 * daily_stats['sem'],
                        alpha=0.3, color='lightblue', label='95% CI')
        
        # Add zero line
        ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        # Mark Forbush event
        ax.axvline(0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Forbush Event')
        
        # Mark typical cooling time (14 days)
        ax.axvline(14, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Day 14')
        
        # Highlight cooling period
        cooling_zone = daily_stats[(daily_stats.index >= 10) & (daily_stats.index <= 20)]
        if len(cooling_zone) > 0 and cooling_zone['mean'].mean() < -0.5:
            ax.axvspan(10, 20, alpha=0.1, color='blue', label='Cooling Period')
        
        ax.set_xlabel('Days Relative to Forbush Event', fontsize=10, fontweight='bold')
        ax.set_ylabel('SST Anomaly (°C)', fontsize=10, fontweight='bold')
        ax.set_title(f'{region}\n(n={len(composite_data)} events)', 
                     fontsize=12, fontweight='bold')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-days_before, days_after)
    
    plt.suptitle('Sea Surface Temperature Response to Forbush Decreases\nComposite Analysis',
                 fontsize=16, fontweight='bold', y=1.00)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

# ============================================================================
# FIGURE 3: STATISTICAL SUMMARY ACROSS ALL REGIONS
# ============================================================================

def plot_regional_summary(output_path='fig3_regional_summary.png'):
    """
    Create bar chart showing SST response across all regions.
    """
    # Data from your analysis
    regions = ['Ceduna', 'GAB', 'KI - E', 'KI - W', 'Mt Gambier', 'Port Fairy',
               'Port Lincoln', 'SVG - NE', 'SVG - NW', 'SVG - SE', 'SVG - SW',
               'Spencer Gulf N', 'Spencer Gulf S', 'Victor Harbor', 
               'Victor Harbour-Mt Gambier']
    
    cooling = [-1.049, -1.089, -0.969, -0.842, -1.350, -1.402, -1.156, -1.436,
               -1.367, -1.463, -1.466, -1.660, -1.342, -1.594, -1.742]
    
    lag_days = [14.5, 14.3, 16.5, 12.9, 16.3, 21.7, 14.9, 13.1, 16.7, 16.2,
                14.7, 15.5, 14.4, 19.4, 16.8]
    
    p_values = [0.0021, 0.0013, 0.0063, 0.0105, 0.0005, 0.0445, 0.0012, 0.0139,
                0.0193, 0.0028, 0.0013, 0.0005, 0.0021, 0.0041, 0.0015]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Mean SST change
    colors = ['darkred' if p < 0.01 else 'indianred' if p < 0.05 else 'lightcoral' 
              for p in p_values]
    
    bars = ax1.barh(regions, cooling, color=colors, edgecolor='black', linewidth=0.5)
    ax1.axvline(0, color='black', linewidth=1)
    ax1.set_xlabel('Mean SST Change (°C)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Region', fontsize=12, fontweight='bold')
    ax1.set_title('SST Cooling After Forbush Decreases\nAll Regions Significant (p < 0.05)',
                  fontsize=14, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # Add legend for significance
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='darkred', label='p < 0.01 (Highly Significant)'),
        Patch(facecolor='indianred', label='0.01 < p < 0.05 (Significant)')
    ]
    ax1.legend(handles=legend_elements, loc='lower right')
    
    # Plot 2: Lag times
    ax2.scatter(lag_days, cooling, s=100, c=colors, edgecolor='black', linewidth=1, alpha=0.7)
    
    for i, region in enumerate(regions):
        if regions[i] in ['GAB', 'Victor Harbor', 'Port Fairy', 'Spencer Gulf N']:
            ax2.annotate(region, (lag_days[i], cooling[i]), 
                        fontsize=8, alpha=0.7,
                        xytext=(5, 5), textcoords='offset points')
    
    ax2.axhline(-1.0, color='gray', linestyle='--', alpha=0.3, label='Mean cooling')
    ax2.axvline(15, color='orange', linestyle='--', alpha=0.5, label='~14 day lag')
    
    ax2.set_xlabel('Lag to Maximum Cooling (days)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Mean SST Change (°C)', fontsize=12, fontweight='bold')
    ax2.set_title('Relationship Between Lag Time and Cooling Magnitude',
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

# ============================================================================
# FIGURE 4: 2024 CASE STUDY
# ============================================================================

def plot_2024_case_study(cr_df, sst_df, forbush_df, 
                         output_path='fig4_2024_case_study.png'):
    """
    Focus on the 2024 period showing potential connection to the HAB event.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    # Filter to 2024
    cr_2024 = cr_df[(cr_df['date'] >= '2024-01-01') & (cr_df['date'] <= '2024-07-01')]
    forbush_2024 = forbush_df[(forbush_df['date'] >= '2024-01-01') & 
                               (forbush_df['date'] <= '2024-07-01')]
    
    # Plot 1: Cosmic rays
    ax1.plot(cr_2024['date'], cr_2024['cosmic_ray_flux'], 
             linewidth=1, color='navy', label='Cosmic Ray Flux')
    
    baseline = cr_2024['cosmic_ray_flux'].rolling(window=27, center=True).median()
    ax1.plot(cr_2024['date'], baseline, 
             linewidth=2, color='orange', alpha=0.8, label='27-day Baseline')
    
    # Mark Forbush events
    for _, event in forbush_2024.iterrows():
        ax1.axvline(event['date'], color='red', alpha=0.5, linewidth=2, linestyle='--')
        ax1.text(event['date'], ax1.get_ylim()[1], 
                f"FD: {event['magnitude']:.1f}%",
                rotation=90, va='top', ha='right', fontsize=9, color='red')
    
    ax1.set_ylabel('Count Rate\n(cts/min)', fontsize=11, fontweight='bold')
    ax1.set_title('2024 Case Study: Forbush Decreases and Ocean Response',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: SST for selected regions
    key_regions = ['GAB', 'Ceduna', 'Port Lincoln', 'Spencer Gulf S']
    colors_map = {'GAB': 'darkblue', 'Ceduna': 'darkgreen', 
                  'Port Lincoln': 'darkred', 'Spencer Gulf S': 'purple'}
    
    for region in key_regions:
        region_data = sst_df[(sst_df['region'] == region) &
                             (sst_df['date'] >= '2024-01-01') &
                             (sst_df['date'] <= '2024-07-01')]
        
        # Calculate anomaly from Jan baseline
        jan_baseline = region_data[region_data['date'] < '2024-02-01']['sst'].mean()
        region_data = region_data.copy()
        region_data['sst_anomaly'] = region_data['sst'] - jan_baseline
        
        ax2.plot(region_data['date'], region_data['sst_anomaly'],
                linewidth=2, label=region, color=colors_map.get(region, 'gray'),
                alpha=0.8)
    
    # Mark expected cooling periods (14 days after each Forbush)
    for _, event in forbush_2024.iterrows():
        cooling_date = event['date'] + pd.Timedelta(days=14)
        ax2.axvline(cooling_date, color='orange', alpha=0.3, linewidth=2, linestyle=':')
    
    # Highlight April-May extreme cooling period
    ax2.axvspan(pd.Timestamp('2024-04-01'), pd.Timestamp('2024-05-31'),
                alpha=0.1, color='blue', label='April-May Extreme Cooling')
    
    ax2.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax2.set_ylabel('SST Anomaly\n(°C vs Jan 2024)', fontsize=11, fontweight='bold')
    ax2.legend(loc='lower left', ncol=2)
    ax2.grid(True, alpha=0.3)
    
    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

# ============================================================================
# FIGURE 5: MECHANISM SCHEMATIC
# ============================================================================

def plot_mechanism_schematic(output_path='fig5_mechanism.png'):
    """
    Create a schematic diagram showing the proposed mechanism.
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(5, 9.5, 'Proposed Mechanism: Solar Activity → Ocean Temperature',
            ha='center', fontsize=16, fontweight='bold')
    
    # Step 1: Solar event
    ax.add_patch(plt.Rectangle((0.5, 7.5), 1.5, 1, facecolor='yellow', 
                               edgecolor='orange', linewidth=2))
    ax.text(1.25, 8, 'Coronal Mass\nEjection (CME)', ha='center', va='center',
            fontsize=10, fontweight='bold')
    
    ax.annotate('', xy=(2.5, 8), xytext=(2, 8),
                arrowprops=dict(arrowstyle='->', lw=2, color='red'))
    
    # Step 2: Forbush decrease
    ax.add_patch(plt.Rectangle((2.5, 7.5), 1.5, 1, facecolor='lightblue',
                               edgecolor='blue', linewidth=2))
    ax.text(3.25, 8, 'Forbush\nDecrease', ha='center', va='center',
            fontsize=10, fontweight='bold')
    ax.text(3.25, 7.2, '(Cosmic Ray ↓)', ha='center', fontsize=8, style='italic')
    
    ax.annotate('', xy=(4.5, 8), xytext=(4, 8),
                arrowprops=dict(arrowstyle='->', lw=2, color='red'))
    ax.text(4.25, 8.3, 'Days 0-7', ha='center', fontsize=8, color='red')
    
    # Step 3: Atmospheric response
    ax.add_patch(plt.Rectangle((4.5, 7.5), 2, 1, facecolor='lightgreen',
                               edgecolor='green', linewidth=2))
    ax.text(5.5, 8, 'Atmospheric\nCirculation Changes', ha='center', va='center',
            fontsize=10, fontweight='bold')
    ax.text(5.5, 7.2, '(Pressure/Wind)', ha='center', fontsize=8, style='italic')
    
    ax.annotate('', xy=(7.5, 7.5), xytext=(6.5, 8),
                arrowprops=dict(arrowstyle='->', lw=2, color='red'))
    ax.text(7, 7.8, 'Days 7-14', ha='center', fontsize=8, color='red')
    
    # Step 4: Ocean response
    ax.add_patch(plt.Rectangle((7.5, 6.5), 2, 1, facecolor='lightcoral',
                               edgecolor='darkred', linewidth=2))
    ax.text(8.5, 7, 'SST Cooling\n~1-1.7°C', ha='center', va='center',
            fontsize=10, fontweight='bold')
    ax.text(8.5, 6.2, '(Upwelling/Mixing)', ha='center', fontsize=8, style='italic')
    
    # Add observations box
    ax.add_patch(plt.Rectangle((0.5, 5), 9, 1, facecolor='lightyellow',
                               edgecolor='gold', linewidth=2))
    ax.text(5, 5.5, 'Observations: 15/15 regions show significant cooling at ~14 day lag (p < 0.05)',
            ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Add biological response (weak)
    ax.annotate('', xy=(8.5, 4.5), xytext=(8.5, 6),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray', linestyle='dashed'))
    ax.text(9, 5.2, 'Weak\nVariable\nTiming', ha='left', fontsize=8, 
            color='gray', style='italic')
    
    ax.add_patch(plt.Rectangle((7.5, 3.5), 2, 1, facecolor='lightgray',
                               edgecolor='gray', linewidth=2, linestyle='dashed'))
    ax.text(8.5, 4, 'Chlorophyll\nResponse?', ha='center', va='center',
            fontsize=10, fontweight='bold', color='gray')
    ax.text(8.5, 3.2, '(2/15 regions, weak)', ha='center', fontsize=8, 
            style='italic', color='gray')
    
    # Add interpretation box
    ax.add_patch(plt.Rectangle((0.5, 1), 9, 1.5, facecolor='white',
                               edgecolor='black', linewidth=2))
    ax.text(5, 2.3, 'Interpretation:', ha='center', fontsize=12, fontweight='bold')
    ax.text(5, 1.8, '• Real physical effect: Solar activity modulates SST via atmospheric coupling',
            ha='center', fontsize=9)
    ax.text(5, 1.5, '• Weak biological response: ~1°C cooling insufficient to drive strong blooms',
            ha='center', fontsize=9)
    ax.text(5, 1.2, '• 2024 HAB: Primarily driven by land-based nutrient loading + seasonal upwelling',
            ha='center', fontsize=9)
    
    # Add "footnote" label
    ax.text(5, 0.3, 'A Scientific Curiosity: Real but Not the Main Story',
            ha='center', fontsize=13, fontweight='bold', style='italic', color='darkblue')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                                                                            ║
    ║          FORBUSH DECREASE - SST CONNECTION VISUALIZATION                  ║
    ║                                                                            ║
    ║   Creating publication-quality figures for a scientific footnote          ║
    ║                                                                            ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    cosmic_ray_csv = 'oulu_cosmic_ray.csv'
    sst_csv = 'sst.csv'
    forbush_csv = 'forbush_events.csv'
    
    # ========================================================================
    # LOAD DATA
    # ========================================================================
    
    print("\n" + "="*80)
    print("LOADING DATA")
    print("="*80)
    
    try:
        cr_df, sst_df, forbush_df = load_all_data(cosmic_ray_csv, sst_csv, forbush_csv)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # ========================================================================
    # CREATE FIGURES
    # ========================================================================
    
    print("\n" + "="*80)
    print("CREATING FIGURES")
    print("="*80 + "\n")
    
    # Figure 1: Cosmic ray time series
    print("Creating Figure 1: Cosmic ray time series...")
    plot_cosmic_ray_timeseries(cr_df, forbush_df)
    
    # Figure 2: SST composite response
    print("\nCreating Figure 2: SST composite response...")
    plot_composite_sst_response(sst_df, forbush_df,
                               regions_to_plot=['GAB', 'Ceduna', 'Port Lincoln', 'Victor Harbor'])
    
    # Figure 3: Regional summary
    print("\nCreating Figure 3: Regional summary...")
    plot_regional_summary()
    
    # Figure 4: 2024 case study
    print("\nCreating Figure 4: 2024 case study...")
    plot_2024_case_study(cr_df, sst_df, forbush_df)
    
    # Figure 5: Mechanism schematic
    print("\nCreating Figure 5: Mechanism schematic...")
    plot_mechanism_schematic()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("""
    ✓ Created 5 publication-quality figures:
    
    1. fig1_cosmic_rays.png
       → Time series of cosmic ray flux (2017-2025) with Forbush events
    
    2. fig2_sst_response.png
       → Composite SST response showing ~14 day cooling lag
    
    3. fig3_regional_summary.png
       → Statistical summary across all 15 regions
    
    4. fig4_2024_case_study.png
       → Detailed analysis of 2024 events
    
    5. fig5_mechanism.png
       → Proposed mechanism schematic
    
    KEY FINDINGS FOR FOOTNOTE:
    
    • Statistically robust: 15/15 regions show significant SST cooling 
      after Forbush decreases (p < 0.05)
    
    • Consistent lag: Mean 14-15 days, remarkably uniform across regions
    
    • Physical mechanism: ~1-1.7°C cooling, likely via atmospheric 
      circulation changes affecting winds/mixing
    
    • Biological response: Weak and inconsistent (2/15 regions)
    
    • 2024 HAB context: Solar activity may have contributed to timing, 
      but primary driver was land-based nutrient loading + seasonal upwelling
    
    CONCLUSION: Real, interesting, but not the main story.
    """)
    
    print("\n" + "="*80)
    print("FILES CREATED")
    print("="*80)
    print("""
    Figures saved as PNG (300 dpi):
      • fig1_cosmic_rays.png
      • fig2_sst_response.png  
      • fig3_regional_summary.png
      • fig4_2024_case_study.png
      • fig5_mechanism.png
    
    Ready for inclusion in reports, presentations, or publications!
    """)

if __name__ == "__main__":
    main()
