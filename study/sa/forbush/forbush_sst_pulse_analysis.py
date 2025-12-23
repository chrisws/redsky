"""
FORBUSH DECREASE & SST PULSE ANALYSIS
======================================
Investigates:
1. Correlations between Forbush decreases and SST changes
2. Detection of short-term SST cooling pulses (upwelling events)
3. Timing relationships between solar events and ocean responses

Background:
- Forbush decreases: Sudden drops in cosmic ray flux from solar events (CMEs)
- Hypothesis: Solar activity → atmospheric changes → ocean circulation changes
- Previous work found no correlation with chlorophyll-a
- Now testing if there's a connection with SST (more direct physical response)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats, signal
from datetime import datetime, timedelta

# ============================================================================
# PART 1: LOAD FORBUSH DECREASE DATA
# ============================================================================

def load_forbush_data(forbush_csv_path):
    """
    Load Forbush decrease event data.
    
    Expected format:
    - date: YYYY-MM-DD of Forbush decrease event
    - magnitude: Percentage decrease in cosmic ray intensity (positive = decrease)
    - duration: Days
    
    Or if you have cosmic ray data:
    - date: YYYY-MM-DD
    - cosmic_ray_intensity: Counts or percentage
    
    Returns DataFrame with Forbush events identified.
    """
    try:
        fd_df = pd.read_csv(forbush_csv_path)
        fd_df['date'] = pd.to_datetime(fd_df['date'])
        
        print(f"Loaded {len(fd_df)} Forbush decrease events")
        print(f"Date range: {fd_df['date'].min()} to {fd_df['date'].max()}")
        
        if 'magnitude' in fd_df.columns:
            print(f"Magnitude range: {fd_df['magnitude'].min():.1f}% to {fd_df['magnitude'].max():.1f}%")
        
        return fd_df
        
    except FileNotFoundError:
        print("❌ Forbush decrease data file not found!")
        print("\nYou can get Forbush decrease data from:")
        print("  1. Neutron Monitor Database: https://www.nmdb.eu")
        print("  2. NOAA Space Weather: https://www.swpc.noaa.gov")
        print("  3. Oulu Cosmic Ray Station: https://cosmicrays.oulu.fi")
        print("\nFor this analysis, you need:")
        print("  - Event dates")
        print("  - Magnitude of decrease (% or absolute)")
        print("  - Optional: Duration, recovery time")
        return None

def detect_forbush_from_timeseries(cosmic_ray_csv_path, threshold_percent=3.0, 
                                   baseline_days=27, min_event_separation_days=5):
    """
    Detect Forbush decreases from Oulu cosmic ray data.
    
    Args:
        cosmic_ray_csv_path: Path to Oulu CSV file
        threshold_percent: Minimum % decrease to count as Forbush event (default 3%)
        baseline_days: Days for rolling baseline (default 27, ~1 solar rotation)
        min_event_separation_days: Min days between separate events (default 5)
    
    Returns:
        DataFrame with columns: date, magnitude, duration_days, min_intensity
    """
    try:
        print("\nLoading Oulu cosmic ray data...")
        
        # Load with proper column names (no header in file)
        cr_df = pd.read_csv(cosmic_ray_csv_path, names=['Timestamp', 'FractionalDate', 
                                                          'UncorrectedCountRate', 
                                                          'CorrectedCountRate', 'Pressure'])
        
        # Parse ISO 8601 timestamp with timezone (e.g., 2017-12-13T00:00:00Z)
        cr_df['date'] = pd.to_datetime(cr_df['Timestamp'], format='ISO8601', errors='coerce', utc=True)
        cr_df = cr_df.dropna(subset=['date'])  # Remove any rows that couldn't be parsed (like header)
        
        # Remove timezone to match SST data (convert to naive datetime)
        cr_df['date'] = cr_df['date'].dt.tz_localize(None)
        
        # Use corrected count rate (pressure-corrected)
        cr_df['intensity'] = pd.to_numeric(cr_df['CorrectedCountRate'], errors='coerce')
        cr_df = cr_df.dropna(subset=['intensity'])
        
        cr_df = cr_df.sort_values('date').reset_index(drop=True)
        
        print(f"Loaded {len(cr_df)} days of cosmic ray data")
        print(f"Date range: {cr_df['date'].min()} to {cr_df['date'].max()}")
        print(f"Mean count rate: {cr_df['intensity'].mean():.0f} cts/min")
        
        # Calculate rolling baseline (centered window for better detection)
        # Using 27 days ≈ one solar rotation period
        cr_df['baseline'] = cr_df['intensity'].rolling(
            window=baseline_days, 
            center=True, 
            min_periods=baseline_days//2
        ).median()
        
        # Fill edges where we can't center
        cr_df['baseline'] = cr_df['baseline'].bfill().ffill()
        
        # Calculate % deviation from baseline
        cr_df['deviation_pct'] = ((cr_df['intensity'] - cr_df['baseline']) / cr_df['baseline']) * 100
        
        # Detect significant drops (Forbush decreases)
        forbush_candidates = cr_df[cr_df['deviation_pct'] < -threshold_percent].copy()
        
        if len(forbush_candidates) == 0:
            print(f"⚠️  No Forbush decreases detected with threshold {threshold_percent}%")
            print(f"   Try lowering the threshold (typical range: 2-5%)")
            return pd.DataFrame()
        
        print(f"\nFound {len(forbush_candidates)} days with CR depression > {threshold_percent}%")
        
        # Group consecutive days into single events
        forbush_candidates['days_since_last'] = forbush_candidates['date'].diff().dt.days
        forbush_candidates['event_id'] = (
            forbush_candidates['days_since_last'] > min_event_separation_days
        ).cumsum()
        
        # Summarize each event
        events = forbush_candidates.groupby('event_id').agg({
            'date': 'first',  # Start date of event
            'deviation_pct': 'min',  # Maximum depression
            'intensity': 'min',  # Minimum count rate
            'baseline': 'first'  # Baseline before event
        }).reset_index(drop=True)
        
        # Calculate event characteristics
        events['magnitude'] = -events['deviation_pct']  # Make positive for clarity
        
        # Calculate duration of each event
        durations = forbush_candidates.groupby('event_id').size()
        events['duration_days'] = durations.values
        
        # Calculate absolute count rate decrease
        events['count_rate_decrease'] = events['baseline'] - events['intensity']
        
        print(f"\nDetected {len(events)} distinct Forbush decrease events")
        print(f"Magnitude range: {events['magnitude'].min():.1f}% to {events['magnitude'].max():.1f}%")
        print(f"Duration range: {events['duration_days'].min():.0f} to {events['duration_days'].max():.0f} days")
        
        # Show notable events
        print("\nLargest Forbush decreases:")
        print("-" * 80)
        top_events = events.nlargest(10, 'magnitude')
        for _, event in top_events.iterrows():
            print(f"{event['date'].strftime('%Y-%m-%d')} | "
                  f"Magnitude: {event['magnitude']:5.1f}% | "
                  f"Duration: {event['duration_days']:2.0f} days | "
                  f"CR drop: {event['count_rate_decrease']:4.0f} cts/min")
        
        # Check for events in early 2024
        events_2024_early = events[
            (events['date'] >= '2024-01-01') & 
            (events['date'] <= '2024-06-30')
        ]
        
        if len(events_2024_early) > 0:
            print("\n" + "🔍" * 40)
            print("EVENTS IN EARLY 2024 (Jan-Jun):")
            print("-" * 80)
            for _, event in events_2024_early.iterrows():
                print(f"{event['date'].strftime('%Y-%m-%d')} | "
                      f"Magnitude: {event['magnitude']:5.1f}% | "
                      f"Duration: {event['duration_days']:2.0f} days")
        
        return events
        
    except Exception as e:
        print(f"❌ Error detecting Forbush events: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# PART 2: DETECT SST COOLING PULSES
# ============================================================================

def detect_sst_cooling_pulses(sst_df, min_cooling_deg=0.5, min_duration_days=2):
    """
    Detect rapid SST cooling events that could indicate upwelling.
    
    Args:
        sst_df: DataFrame with columns [date, region, sst]
        min_cooling_deg: Minimum temperature drop (°C)
        min_duration_days: Minimum duration to count as pulse
    
    Returns:
        DataFrame of cooling pulse events
    """
    print("\n" + "="*80)
    print("DETECTING SST COOLING PULSES")
    print("="*80)
    
    regions = sst_df['region'].unique()
    all_pulses = []
    
    for region in regions:
        region_data = sst_df[sst_df['region'] == region].copy()
        region_data = region_data.sort_values('date')
        
        # Calculate rate of change
        region_data['sst_change'] = region_data['sst'].diff()
        region_data['sst_change_rate'] = region_data['sst_change'] / region_data['date'].diff().dt.days
        
        # Detect cooling events (negative change)
        cooling = region_data[region_data['sst_change'] < -min_cooling_deg].copy()
        
        if len(cooling) == 0:
            continue
        
        # Group consecutive cooling days
        cooling['days_since_last'] = cooling['date'].diff().dt.days
        cooling['pulse_id'] = (cooling['days_since_last'] > 3).cumsum()
        
        # Summarize each pulse
        pulses = cooling.groupby('pulse_id').agg({
            'date': 'first',
            'sst': 'first',
            'sst_change': 'sum'
        }).reset_index()
        
        pulses['region'] = region
        pulses['cooling_magnitude'] = -pulses['sst_change']
        
        # Filter by minimum duration
        pulse_lengths = cooling.groupby('pulse_id').size()
        pulses['duration_days'] = pulse_lengths.values
        pulses = pulses[pulses['duration_days'] >= min_duration_days]
        
        all_pulses.append(pulses[['date', 'region', 'cooling_magnitude', 'duration_days', 'sst']])
    
    if len(all_pulses) > 0:
        pulse_df = pd.concat(all_pulses, ignore_index=True)
        pulse_df = pulse_df.sort_values('date')
        
        print(f"\nDetected {len(pulse_df)} cooling pulse events")
        print(f"Date range: {pulse_df['date'].min()} to {pulse_df['date'].max()}")
        print(f"Cooling magnitude range: {pulse_df['cooling_magnitude'].min():.2f}°C to {pulse_df['cooling_magnitude'].max():.2f}°C")
        
        # Show examples
        print("\nExample cooling pulses:")
        print("-" * 80)
        for _, pulse in pulse_df.head(10).iterrows():
            print(f"{pulse['date'].strftime('%Y-%m-%d')} | {pulse['region']:20s} | "
                  f"Δ={pulse['cooling_magnitude']:5.2f}°C | Duration: {pulse['duration_days']:.0f} days")
        
        return pulse_df
    else:
        print("No cooling pulses detected with current thresholds")
        return pd.DataFrame()

def analyze_sst_variability(sst_df):
    """
    Calculate SST variability metrics to understand typical fluctuations.
    Helps set appropriate thresholds for pulse detection.
    """
    print("\n" + "="*80)
    print("SST VARIABILITY ANALYSIS")
    print("="*80)
    
    regions = sst_df['region'].unique()
    
    for region in regions[:5]:  # Show first 5 as examples
        region_data = sst_df[sst_df['region'] == region].copy()
        region_data = region_data.sort_values('date')
        region_data['sst_change'] = region_data['sst'].diff()
        
        print(f"\n{region}:")
        print(f"  Mean daily SST change: {region_data['sst_change'].mean():.3f}°C")
        print(f"  Std daily SST change: {region_data['sst_change'].std():.3f}°C")
        print(f"  Max cooling (single day): {region_data['sst_change'].min():.2f}°C")
        print(f"  Max warming (single day): {region_data['sst_change'].max():.2f}°C")
        print(f"  95th percentile cooling: {np.percentile(region_data['sst_change'].dropna(), 5):.2f}°C")

# ============================================================================
# PART 3: FORBUSH DECREASE - SST CORRELATION ANALYSIS
# ============================================================================

def analyze_forbush_sst_correlation(sst_df, forbush_df, max_lag_days=30):
    """
    Analyze correlation between Forbush decreases and SST changes.
    
    Tests:
    1. Do SST drops occur after Forbush decreases?
    2. Is there a characteristic lag time?
    3. Are stronger Forbush events associated with larger SST changes?
    """
    if forbush_df is None or len(forbush_df) == 0:
        print("No Forbush decrease data available for correlation analysis")
        return None
    
    print("\n" + "="*80)
    print("FORBUSH DECREASE - SST CORRELATION ANALYSIS")
    print("="*80)
    
    regions = sst_df['region'].unique()
    results = []
    
    for region in regions:
        print(f"\n{region}:")
        print("-" * 40)
        
        region_data = sst_df[sst_df['region'] == region].copy()
        region_data = region_data.sort_values('date')
        
        # For each Forbush event, measure SST response
        forbush_responses = []
        
        for _, fd_event in forbush_df.iterrows():
            fd_date = fd_event['date']
            
            # Get SST at Forbush event date
            sst_at_event = region_data[
                (region_data['date'] >= fd_date) & 
                (region_data['date'] < fd_date + timedelta(days=1))
            ]['sst'].values
            
            if len(sst_at_event) == 0:
                continue
            
            baseline_sst = sst_at_event[0]
            
            # Measure SST change over next max_lag_days
            post_event = region_data[
                (region_data['date'] > fd_date) &
                (region_data['date'] <= fd_date + timedelta(days=max_lag_days))
            ].copy()
            
            if len(post_event) == 0:
                continue
            
            post_event['sst_change'] = post_event['sst'] - baseline_sst
            post_event['days_after'] = (post_event['date'] - fd_date).dt.days
            
            # Find maximum cooling and when it occurred
            min_sst_idx = post_event['sst_change'].idxmin()
            max_cooling = post_event.loc[min_sst_idx, 'sst_change']
            lag_days = post_event.loc[min_sst_idx, 'days_after']
            
            forbush_responses.append({
                'fd_date': fd_date,
                'fd_magnitude': fd_event.get('magnitude', np.nan),
                'max_cooling': max_cooling,
                'lag_days': lag_days,
                'baseline_sst': baseline_sst
            })
        
        if len(forbush_responses) == 0:
            print("  No overlapping data with Forbush events")
            continue
        
        response_df = pd.DataFrame(forbush_responses)
        
        # Statistical analysis
        mean_cooling = response_df['max_cooling'].mean()
        mean_lag = response_df['lag_days'].mean()
        
        print(f"  N events analyzed: {len(response_df)}")
        print(f"  Mean SST change after Forbush: {mean_cooling:.3f}°C")
        print(f"  Mean lag to max cooling: {mean_lag:.1f} days")
        
        # Test if cooling is significant (different from zero)
        t_stat, p_value = stats.ttest_1samp(response_df['max_cooling'], 0)
        
        if p_value < 0.05:
            if mean_cooling < 0:
                print(f"  ✓ SIGNIFICANT cooling after Forbush (p={p_value:.4f})")
            else:
                print(f"  ✓ SIGNIFICANT warming after Forbush (p={p_value:.4f})")
        else:
            print(f"  ✗ No significant SST change (p={p_value:.4f})")
        
        # Test correlation between Forbush magnitude and SST change
        if 'magnitude' in forbush_df.columns and not response_df['fd_magnitude'].isna().all():
            corr = stats.spearmanr(
                response_df['fd_magnitude'].dropna(),
                response_df.loc[response_df['fd_magnitude'].notna(), 'max_cooling']
            )
            print(f"  Correlation (Forbush magnitude vs SST change): r={corr[0]:.3f}, p={corr[1]:.4f}")
            if corr[1] < 0.05:
                print(f"    ✓ Stronger Forbush events {'→ more cooling' if corr[0] < 0 else '→ more warming'}")
        
        results.append({
            'region': region,
            'n_events': len(response_df),
            'mean_sst_change': mean_cooling,
            'mean_lag_days': mean_lag,
            'p_value': p_value,
            'significant': p_value < 0.05
        })
    
    results_df = pd.DataFrame(results)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY: FORBUSH-SST CORRELATION")
    print("="*80)
    
    significant_regions = results_df[results_df['significant']]
    print(f"\nRegions with significant SST response: {len(significant_regions)}/{len(results_df)}")
    
    if len(significant_regions) > 0:
        print("\nSignificant correlations:")
        for _, row in significant_regions.iterrows():
            direction = "COOLING" if row['mean_sst_change'] < 0 else "WARMING"
            print(f"  {row['region']:25s}: {row['mean_sst_change']:+6.3f}°C after {row['mean_lag_days']:.0f} days ({direction})")
    
    return results_df, forbush_responses

# ============================================================================
# PART 4: TEMPORAL COINCIDENCE ANALYSIS
# ============================================================================

def analyze_temporal_coincidence(cooling_pulses_df, forbush_df, window_days=14):
    """
    Check if cooling pulses tend to occur near Forbush decrease events.
    
    Args:
        window_days: Consider events within this many days as "coincident"
    """
    if forbush_df is None or len(forbush_df) == 0:
        print("No Forbush data for coincidence analysis")
        return
    
    if len(cooling_pulses_df) == 0:
        print("No cooling pulses detected for coincidence analysis")
        return
    
    print("\n" + "="*80)
    print("TEMPORAL COINCIDENCE ANALYSIS")
    print("="*80)
    print(f"Looking for cooling pulses within ±{window_days} days of Forbush events")
    
    coincidences = []
    
    for _, pulse in cooling_pulses_df.iterrows():
        pulse_date = pulse['date']
        
        # Find nearest Forbush event
        time_diffs = np.abs((forbush_df['date'] - pulse_date).dt.days)
        nearest_idx = time_diffs.idxmin()
        nearest_fd = forbush_df.loc[nearest_idx]
        days_apart = (pulse_date - nearest_fd['date']).days
        
        if abs(days_apart) <= window_days:
            coincidences.append({
                'pulse_date': pulse_date,
                'pulse_region': pulse['region'],
                'pulse_magnitude': pulse['cooling_magnitude'],
                'fd_date': nearest_fd['date'],
                'fd_magnitude': nearest_fd.get('magnitude', np.nan),
                'days_apart': days_apart
            })
    
    print(f"\nFound {len(coincidences)} cooling pulses within ±{window_days} days of Forbush events")
    print(f"Out of {len(cooling_pulses_df)} total cooling pulses ({100*len(coincidences)/len(cooling_pulses_df):.1f}%)")
    
    # Compare to random expectation
    total_days = (cooling_pulses_df['date'].max() - cooling_pulses_df['date'].min()).days
    n_forbush = len(forbush_df)
    expected_coincidence_rate = (2 * window_days * n_forbush) / total_days
    expected_coincidences = expected_coincidence_rate * len(cooling_pulses_df)
    
    print(f"\nRandom expectation: {expected_coincidences:.1f} coincidences")
    print(f"Observed: {len(coincidences)}")
    
    if len(coincidences) > expected_coincidences * 1.5:
        print("  ✓ MORE coincidences than expected by chance!")
    elif len(coincidences) < expected_coincidences * 0.5:
        print("  → FEWER coincidences than expected")
    else:
        print("  → Consistent with random chance")
    
    if len(coincidences) > 0:
        coinc_df = pd.DataFrame(coincidences)
        print("\nExamples of coincident events:")
        print("-" * 80)
        for _, c in coinc_df.head(10).iterrows():
            print(f"Forbush: {c['fd_date'].strftime('%Y-%m-%d')} → "
                  f"Cooling pulse {c['days_apart']:+3.0f} days later: "
                  f"{c['pulse_region']:20s} (Δ={c['pulse_magnitude']:.2f}°C)")
        
        return coinc_df
    
    return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                                                                            ║
    ║        FORBUSH DECREASE & SST PULSE ANALYSIS                               ║
    ║                                                                            ║
    ║   Testing: Do solar events affect ocean temperatures?                     ║
    ║                                                                            ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # ========================================================================
    # CONFIGURATION - UPDATE THESE PATHS
    # ========================================================================
    
    sst_csv = 'sst.csv'  # Your SST data
    
    # Forbush decrease data - choose ONE:
    # Option 1: You have Oulu cosmic ray data (RECOMMENDED)
    cosmic_ray_csv = 'oulu_cosmic_ray.csv'  # Your Oulu data file
    
    # Option 2: You have a pre-compiled list of Forbush events
    # forbush_csv = 'forbush_events.csv'  # Format: date, magnitude
    
    # ========================================================================
    # LOAD DATA
    # ========================================================================
    
    print("\nStep 1: Loading SST data...")
    try:
        sst_df = pd.read_csv(sst_csv)
        sst_df['date'] = pd.to_datetime(sst_df['date'], format='%Y%m%d')
        
        # Melt to long format
        sst_long = sst_df.melt(
            id_vars=['date'],
            var_name='region',
            value_name='sst'
        )
        sst_long = sst_long.dropna(subset=['sst'])
        sst_long = sst_long.sort_values(['region', 'date'])
        
        print(f"✓ Loaded {len(sst_long)} SST observations")
        
    except Exception as e:
        print(f"❌ Error loading SST data: {e}")
        return
    
    print("\nStep 2: Loading Forbush decrease data...")
    
    # Option 1: Detect from Oulu cosmic ray data (RECOMMENDED)
    cosmic_ray_csv = 'oulu_cosmic_ray.csv'  # Your Oulu data file
    try:
        forbush_df = detect_forbush_from_timeseries(
            cosmic_ray_csv,
            threshold_percent=3.0,  # Adjust if needed (2-5% typical)
            baseline_days=27,       # One solar rotation
            min_event_separation_days=5
        )
        if forbush_df is not None and len(forbush_df) > 0:
            print("✓ Forbush events detected from cosmic ray data")
        else:
            forbush_df = None
    except FileNotFoundError:
        print(f"❌ Cosmic ray data file not found: {cosmic_ray_csv}")
        print("   Please download data from: https://cosmicrays.oulu.fi")
        forbush_df = None
    except Exception as e:
        print(f"❌ Error processing cosmic ray data: {e}")
        forbush_df = None
    
    # Option 2: Load pre-compiled Forbush event list (if you have one)
    # forbush_csv = 'forbush_events.csv'
    # forbush_df = load_forbush_data(forbush_csv)
    
    if forbush_df is None or len(forbush_df) == 0:
        print("\n⚠️  Continuing without Forbush data - will only analyze SST pulses")
        print("    To get cosmic ray data:")
        print("    1. Visit: https://cosmicrays.oulu.fi")
        print("    2. Select 'Download data'")
        print("    3. Choose date range: 2017-01-01 to 2025-09-30")
        print("    4. Format: CSV with corrected count rates")
    
    # ========================================================================
    # ANALYSIS
    # ========================================================================
    
    # Analyze SST variability (helps set thresholds)
    analyze_sst_variability(sst_long)
    
    # Detect cooling pulses
    cooling_pulses = detect_sst_cooling_pulses(
        sst_long,
        min_cooling_deg=1.0,  # Adjust based on variability analysis
        min_duration_days=2
    )
    
    # Forbush-SST correlation (if Forbush data available)
    if forbush_df is not None:
        correlation_results, responses = analyze_forbush_sst_correlation(
            sst_long,
            forbush_df,
            max_lag_days=30
        )
        
        # Temporal coincidence
        if len(cooling_pulses) > 0:
            coincidences = analyze_temporal_coincidence(
                cooling_pulses,
                forbush_df,
                window_days=14
            )

        forbush_df.to_csv('forbush_events.csv', index=False)
            
    # ========================================================================
    # INTERPRETATION
    # ========================================================================
    
    print("\n" + "="*80)
    print("INTERPRETATION GUIDE")
    print("="*80)
    print("""
    If you find:
    
    ✓ Significant SST cooling after Forbush events (p < 0.05)
      → Suggests solar activity may influence ocean temperatures
      → Mechanism could be: CME → atmospheric circulation changes → 
        wind patterns → upwelling/mixing
    
    ✓ Correlation between Forbush magnitude and SST change magnitude
      → Stronger solar events → stronger ocean response
      → Supports causal relationship
    
    ✓ More temporal coincidences than expected by chance
      → Timing alignment supports connection
      → But doesn't prove causation (could be seasonal confounding)
    
    ✗ No significant correlations
      → Solar events don't appear to directly affect SST
      → Matches your previous finding with chlorophyll-a
      → Ocean processes likely dominated by local meteorology
    
    MECHANISM HYPOTHESES:
    1. Direct: CME → ionosphere changes → atmospheric electricity → 
       cloud formation → radiation budget → SST
    2. Indirect: CME → magnetosphere → atmospheric circulation → 
       wind patterns → upwelling → SST
    3. Null: No connection - both vary independently
    """)
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
    1. If correlations found: Investigate mechanism
       - Get wind data for same periods
       - Check atmospheric pressure patterns
       - Look at cloud cover changes
    
    2. Focus on April-May 2024 cooling event
       - Were there Forbush decreases then?
       - Or was it purely meteorological?
    
    3. Compare with other solar indices
       - Solar wind speed
       - Geomagnetic indices (Kp, Dst)
       - Solar flux (F10.7)
    """)

if __name__ == "__main__":
    main()
