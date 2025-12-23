"""
FORBUSH DECREASE - CHLOROPHYLL-A LAG ANALYSIS
==============================================
Since we found SST cools ~14 days after Forbush decreases, let's test if
chlorophyll blooms at longer lags:

Hypothesis: 
  Forbush decrease → 14 days → SST cooling → ?? days → Chlorophyll bloom

Testing lags: 0-90 days to capture:
  - Immediate response (0-14 days) - not expected based on previous null result
  - SST response time (14 days)
  - SST + biological response (14-30 days)
  - Full bloom development (30-60 days)
  - Extended cascade (60-90 days)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from datetime import datetime, timedelta

# ============================================================================
# LOAD DATA
# ============================================================================

def load_chlorophyll_data(chl_csv_path):
    """Load chlorophyll-a data in wide format."""
    try:
        chl_df = pd.read_csv(chl_csv_path)
        chl_df['date'] = pd.to_datetime(chl_df['date'], format='%Y%m%d')
        
        # Melt to long format
        chl_long = chl_df.melt(
            id_vars=['date'],
            var_name='region',
            value_name='chlorophyll'
        )
        chl_long = chl_long.dropna(subset=['chlorophyll'])
        chl_long = chl_long.sort_values(['region', 'date'])
        
        print(f"✓ Loaded {len(chl_long)} chlorophyll observations")
        print(f"  Date range: {chl_long['date'].min()} to {chl_long['date'].max()}")
        print(f"  Regions: {chl_long['region'].nunique()}")
        
        return chl_long
        
    except Exception as e:
        print(f"❌ Error loading chlorophyll data: {e}")
        return None

def load_forbush_events(forbush_csv_path):
    """Load pre-detected Forbush events."""
    try:
        fd_df = pd.read_csv(forbush_csv_path)
        fd_df['date'] = pd.to_datetime(fd_df['date'])
        
        print(f"✓ Loaded {len(fd_df)} Forbush decrease events")
        print(f"  Date range: {fd_df['date'].min()} to {fd_df['date'].max()}")
        
        if 'magnitude' in fd_df.columns:
            print(f"  Magnitude range: {fd_df['magnitude'].min():.1f}% to {fd_df['magnitude'].max():.1f}%")
        
        return fd_df
        
    except Exception as e:
        print(f"❌ Error loading Forbush data: {e}")
        return None

# ============================================================================
# MULTI-LAG CORRELATION ANALYSIS
# ============================================================================

def analyze_chlorophyll_response_multilag(chl_df, forbush_df, 
                                          max_lag_days=90, lag_step=1):
    """
    Test chlorophyll response at multiple lag times after Forbush events.
    
    Args:
        chl_df: Chlorophyll data (date, region, chlorophyll)
        forbush_df: Forbush events (date, magnitude, ...)
        max_lag_days: Maximum lag to test
        lag_step: Step between tested lags
    
    Returns:
        DataFrame with correlation at each lag for each region
    """
    print("\n" + "="*80)
    print("MULTI-LAG CORRELATION ANALYSIS")
    print("="*80)
    print(f"Testing lags from 0 to {max_lag_days} days (step={lag_step})")
    
    regions = chl_df['region'].unique()
    lags_to_test = range(0, max_lag_days + 1, lag_step)
    
    all_results = []
    
    for region in regions:
        print(f"\nAnalyzing {region}...")
        
        region_data = chl_df[chl_df['region'] == region].copy()
        region_data = region_data.sort_values('date')
        
        # Calculate baseline chlorophyll for this region
        baseline_chl = region_data['chlorophyll'].median()
        
        lag_correlations = []
        
        for lag_days in lags_to_test:
            # For each Forbush event, measure chlorophyll at this specific lag
            responses = []
            
            for _, fd_event in forbush_df.iterrows():
                fd_date = pd.Timestamp(fd_event['date'])
                target_date = fd_date + pd.Timedelta(days=lag_days)
                
                # Get chlorophyll within ±3 days of target date
                chl_window = region_data[
                    (region_data['date'] >= target_date - pd.Timedelta(days=3)) &
                    (region_data['date'] <= target_date + pd.Timedelta(days=3))
                ]
                
                if len(chl_window) > 0:
                    # Use mean chlorophyll in window
                    chl_value = chl_window['chlorophyll'].mean()
                    # Calculate anomaly from baseline
                    chl_anomaly = chl_value - baseline_chl
                    
                    responses.append({
                        'fd_magnitude': fd_event.get('magnitude', np.nan),
                        'chl_anomaly': chl_anomaly,
                        'chl_value': chl_value
                    })
            
            if len(responses) >= 5:  # Need at least 5 events
                resp_df = pd.DataFrame(responses)
                
                # Test if chlorophyll anomaly is significantly > 0
                t_stat, p_value = stats.ttest_1samp(resp_df['chl_anomaly'], 0)
                
                # Calculate mean response
                mean_anomaly = resp_df['chl_anomaly'].mean()
                
                # Test correlation with Forbush magnitude (if available)
                if 'magnitude' in forbush_df.columns and not resp_df['fd_magnitude'].isna().all():
                    corr_mag = stats.spearmanr(
                        resp_df['fd_magnitude'].dropna(),
                        resp_df.loc[resp_df['fd_magnitude'].notna(), 'chl_anomaly']
                    )
                    corr_r = corr_mag[0]
                    corr_p = corr_mag[1]
                else:
                    corr_r = np.nan
                    corr_p = np.nan
                
                lag_correlations.append({
                    'region': region,
                    'lag_days': lag_days,
                    'n_events': len(resp_df),
                    'mean_chl_anomaly': mean_anomaly,
                    'p_value': p_value,
                    'significant': p_value < 0.05,
                    'corr_with_magnitude': corr_r,
                    'corr_p_value': corr_p
                })
        
        all_results.extend(lag_correlations)
    
    results_df = pd.DataFrame(all_results)
    return results_df

# ============================================================================
# IDENTIFY OPTIMAL LAG PER REGION
# ============================================================================

def find_optimal_lags(results_df):
    """
    For each region, find the lag with strongest chlorophyll response.
    """
    print("\n" + "="*80)
    print("OPTIMAL LAG ANALYSIS")
    print("="*80)
    
    regions = results_df['region'].unique()
    optimal_lags = []
    
    for region in regions:
        region_results = results_df[results_df['region'] == region].copy()
        
        # Find lag with maximum mean chlorophyll anomaly
        max_anomaly_idx = region_results['mean_chl_anomaly'].idxmax()
        optimal = region_results.loc[max_anomaly_idx]
        
        # Find lag with minimum p-value (most significant)
        min_p_idx = region_results['p_value'].idxmin()
        most_sig = region_results.loc[min_p_idx]
        
        optimal_lags.append({
            'region': region,
            'lag_max_response': optimal['lag_days'],
            'max_chl_anomaly': optimal['mean_chl_anomaly'],
            'p_value_at_max': optimal['p_value'],
            'lag_most_significant': most_sig['lag_days'],
            'p_value_min': most_sig['p_value'],
            'chl_anomaly_at_min_p': most_sig['mean_chl_anomaly']
        })
    
    optimal_df = pd.DataFrame(optimal_lags)
    
    print("\nOPTIMAL LAGS BY REGION:")
    print("-" * 80)
    print(f"{'Region':<25s} | {'Lag (max Chl)':<15s} | {'Chl Anomaly':<12s} | {'p-value'}")
    print("-" * 80)
    
    for _, row in optimal_df.iterrows():
        sig_marker = " ✓" if row['p_value_at_max'] < 0.05 else ""
        print(f"{row['region']:<25s} | {row['lag_max_response']:>5.0f} days      | "
              f"{row['max_chl_anomaly']:>+10.3f} | {row['p_value_at_max']:.4f}{sig_marker}")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS:")
    print("="*80)
    
    significant = optimal_df[optimal_df['p_value_at_max'] < 0.05]
    print(f"Regions with significant response: {len(significant)}/{len(optimal_df)}")
    
    if len(significant) > 0:
        print(f"\nMean optimal lag (significant regions): {significant['lag_max_response'].mean():.1f} days")
        print(f"Median optimal lag (significant regions): {significant['lag_max_response'].median():.1f} days")
        print(f"Range: {significant['lag_max_response'].min():.0f} - {significant['lag_max_response'].max():.0f} days")
        
        print("\nSignificant responses:")
        for _, row in significant.iterrows():
            print(f"  {row['region']:25s}: {row['max_chl_anomaly']:+.3f} mg/m³ at {row['lag_max_response']:.0f} days")
    
    return optimal_df

# ============================================================================
# SPECIFIC LAG ANALYSIS (14, 30, 45, 60 DAYS)
# ============================================================================

def analyze_specific_lags(chl_df, forbush_df, test_lags=[14, 30, 45, 60]):
    """
    Test specific lag hypotheses:
    - 14 days: SST response time
    - 30 days: SST + fast biological response
    - 45 days: Medium bloom development
    - 60 days: Full bloom development (matches your earlier findings)
    """
    print("\n" + "="*80)
    print("SPECIFIC LAG HYPOTHESIS TESTING")
    print("="*80)
    print(f"Testing lags: {test_lags} days")
    
    regions = chl_df['region'].unique()
    
    for lag in test_lags:
        print(f"\n{'='*80}")
        print(f"LAG: {lag} DAYS")
        print(f"{'='*80}")
        
        sig_count = 0
        
        for region in regions:
            region_data = chl_df[chl_df['region'] == region].copy()
            baseline_chl = region_data['chlorophyll'].median()
            
            responses = []
            
            for _, fd_event in forbush_df.iterrows():
                fd_date = pd.Timestamp(fd_event['date'])
                target_date = fd_date + pd.Timedelta(days=lag)
                
                chl_window = region_data[
                    (region_data['date'] >= target_date - pd.Timedelta(days=3)) &
                    (region_data['date'] <= target_date + pd.Timedelta(days=3))
                ]
                
                if len(chl_window) > 0:
                    chl_anomaly = chl_window['chlorophyll'].mean() - baseline_chl
                    responses.append(chl_anomaly)
            
            if len(responses) >= 5:
                t_stat, p_value = stats.ttest_1samp(responses, 0)
                mean_anomaly = np.mean(responses)
                
                if p_value < 0.05:
                    sig_marker = "✓ SIGNIFICANT"
                    sig_count += 1
                else:
                    sig_marker = ""
                
                print(f"{region:25s}: {mean_anomaly:+8.3f} mg/m³ (p={p_value:.4f}) {sig_marker}")
        
        print(f"\nSignificant responses at {lag} days: {sig_count}/{len(regions)}")

# ============================================================================
# VISUALIZATION
# ============================================================================

def plot_lag_correlation_heatmap(results_df, output_path='forbush_chl_lag_heatmap.png'):
    """
    Create heatmap showing correlation strength at each lag for each region.
    """
    # Pivot data for heatmap
    pivot = results_df.pivot(index='region', columns='lag_days', values='mean_chl_anomaly')
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Mean chlorophyll anomaly
    im1 = ax1.imshow(pivot.values, aspect='auto', cmap='RdBu_r', 
                     vmin=-0.5, vmax=0.5, interpolation='nearest')
    ax1.set_yticks(range(len(pivot.index)))
    ax1.set_yticklabels(pivot.index)
    ax1.set_xlabel('Lag (days)')
    ax1.set_ylabel('Region')
    ax1.set_title('Mean Chlorophyll-a Anomaly After Forbush Decreases')
    
    # Add lag labels every 10 days
    lag_ticks = range(0, len(pivot.columns), 10)
    ax1.set_xticks(lag_ticks)
    ax1.set_xticklabels([pivot.columns[i] for i in lag_ticks])
    
    plt.colorbar(im1, ax=ax1, label='Chlorophyll anomaly (mg/m³)')
    
    # Plot 2: Statistical significance
    pivot_sig = results_df.pivot(index='region', columns='lag_days', values='p_value')
    sig_mask = (pivot_sig.values < 0.05).astype(float)
    
    im2 = ax2.imshow(sig_mask, aspect='auto', cmap='Greys', 
                     vmin=0, vmax=1, interpolation='nearest')
    ax2.set_yticks(range(len(pivot_sig.index)))
    ax2.set_yticklabels(pivot_sig.index)
    ax2.set_xlabel('Lag (days)')
    ax2.set_ylabel('Region')
    ax2.set_title('Statistical Significance (p < 0.05 = black)')
    ax2.set_xticks(lag_ticks)
    ax2.set_xticklabels([pivot_sig.columns[i] for i in lag_ticks])
    
    # Add vertical line at 14 days (SST response time)
    for ax in [ax1, ax2]:
        ax.axvline(x=14, color='yellow', linestyle='--', linewidth=2, alpha=0.7)
        ax.text(14, -0.5, '14d (SST)', ha='center', va='top', 
                color='yellow', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Heatmap saved to: {output_path}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                                                                            ║
    ║     FORBUSH DECREASE → CHLOROPHYLL BLOOM LAG ANALYSIS                     ║
    ║                                                                            ║
    ║  Known: Forbush → 14 days → SST cooling                                   ║
    ║  Question: Forbush → ?? days → Chlorophyll bloom?                         ║
    ║                                                                            ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    chl_csv = 'chlr-a.csv'
    forbush_csv = 'forbush_events.csv'  # Output from previous script
    
    # ========================================================================
    # LOAD DATA
    # ========================================================================
    
    print("Step 1: Loading data...")
    print("="*80)
    
    chl_df = load_chlorophyll_data(chl_csv)
    forbush_df = load_forbush_events(forbush_csv)
    
    if chl_df is None or forbush_df is None:
        print("\n❌ Cannot proceed without both datasets")
        return
    
    # ========================================================================
    # ANALYSIS
    # ========================================================================
    
    print("\n" + "="*80)
    print("Running multi-lag analysis...")
    print("="*80)
    
    # Test all lags from 0 to 90 days
    results_df = analyze_chlorophyll_response_multilag(
        chl_df, 
        forbush_df,
        max_lag_days=90,
        lag_step=1  # Test every day for precision
    )
    
    # Find optimal lags
    optimal_lags = find_optimal_lags(results_df)
    
    # Test specific hypothesis lags
    analyze_specific_lags(chl_df, forbush_df, test_lags=[14, 30, 45, 60])
    
    # Create visualization
    plot_lag_correlation_heatmap(results_df)
    
    # ========================================================================
    # SAVE RESULTS
    # ========================================================================
    
    results_df.to_csv('forbush_chlorophyll_lag_results.csv', index=False)
    optimal_lags.to_csv('forbush_chlorophyll_optimal_lags.csv', index=False)
    print("\n✓ Results saved to:")
    print("  - forbush_chlorophyll_lag_results.csv")
    print("  - forbush_chlorophyll_optimal_lags.csv")
    print("  - forbush_chl_lag_heatmap.png")
    
    # ========================================================================
    # INTERPRETATION
    # ========================================================================
    
    print("\n" + "="*80)
    print("INTERPRETATION GUIDE")
    print("="*80)
    print("""
    Key patterns to look for:
    
    1. NO SIGNIFICANT RESPONSE AT ANY LAG
       → Biology truly doesn't track solar events
       → SST changes too brief or small for phytoplankton
    
    2. SIGNIFICANT RESPONSE AT ~30-45 DAYS
       → SST cooling (14d) + bloom development (15-30d) = 30-45d total
       → This would confirm the cascade: Forbush → SST → Nutrients → Bloom
    
    3. SIGNIFICANT RESPONSE AT ~60 DAYS
       → Matches your earlier correlation analysis optimal lags!
       → Suggests full bloom development time
    
    4. MULTIPLE PEAKS AT DIFFERENT LAGS
       → Different regions/species respond at different rates
       → Fast bloomers at 30d, slow bloomers at 60d
    
    5. SIGNIFICANT RESPONSE ONLY IN SOME REGIONS
       → Western upwelling zones might show it, eastern zones might not
       → Matches your regional differences in SST-chlorophyll correlation
    
    MECHANISM CHAIN (if we find significant lags):
    
    Forbush decrease → 14 days → SST cooling → X days → Chl bloom
                        (confirmed)            (testing)
    
    Total lag = 14 + X days
    
    If X ≈ 15-30 days: Fast biological response (opportunistic species)
    If X ≈ 30-45 days: Medium response (typical bloom development)
    If X ≈ 45-60 days: Slow response (succession, multiple generations)
    """)

if __name__ == "__main__":
    main()
