import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import pandas as pd
import os
from matplotlib.patches import Rectangle
from matplotlib.colors import TwoSlopeNorm
from viirs_regions import get_regions


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def calculate_sector_trends(csv_path, regions):
    """
    Calculate temperature trends for each region from the CSV data.

    The CSV is expected to have a YYYYMMDD date index (first column) and one
    column per region containing daily-mean SST values (°C).  NaN / missing
    values are normal for cloudy or night-gap days.

    Two improvements over a raw OLS trend:

    1. SEASONAL ANOMALIES
       The raw SST signal has a large seasonal cycle (~8°C peak-to-trough for
       Tasmania).  If a region's clear-sky sampling is unevenly distributed
       across seasons between years (a real risk at <40% coverage), the
       seasonal cycle contaminates the trend.  We remove it by subtracting
       the climatological day-of-year mean before regressing.

    2. COVERAGE-WEIGHTED UNCERTAINTY
       Low-coverage sectors are noisier because they sample a smaller,
       potentially biased subset of days.  We inflate std_err by
       1 / sqrt(coverage_fraction) so the uncertainty band honestly
       reflects the reduced effective sample.  The slope itself is unchanged;
       only the reported confidence is widened.

    Returns a dict keyed by region name, each value a sub-dict with:
        slope_per_decade      – °C / decade from anomaly regression
        p_value               – two-tailed p-value (coverage-adjusted)
        r_squared             – r² of the anomaly regression
        std_err_decade        – coverage-adjusted ±1σ in °C / decade
        std_err_raw           – unadjusted OLS std_err (for reference)
        n                     – number of valid observations
        mean_sst              – mean raw SST over the record (°C)
        coverage_pct          – % of rows that have a non-NaN value
        seasonal_cycle_range  – peak-to-trough amplitude of the DOY climatology
    """
    try:
        from scipy.stats import linregress, t as t_dist

        # index_col=0 keeps the date column as the DataFrame index and
        # prevents pandas from misreading it as a float SST value.
        df = pd.read_csv(csv_path, index_col=0)
        df.index = pd.to_datetime(df.index.astype(str), format="%Y%m%d")
        df.index.name = "date"
        df = df.sort_index()

        n_dupes = df.index.duplicated().sum()
        if n_dupes:
            print(f"  Warning: {n_dupes} duplicate dates found – keeping first occurrence")
            df = df[~df.index.duplicated(keep="first")]

        total_rows   = len(df)
        decimal_year = (df.index.year + df.index.dayofyear / 365.25).to_numpy()
        doy          = df.index.dayofyear.to_numpy()   # 1–366

        sector_trends = {}
        for region_name in regions.keys():
            if region_name not in df.columns:
                continue

            raw  = df[region_name].to_numpy(dtype=float, na_value=np.nan)
            mask = ~np.isnan(raw)
            n    = int(mask.sum())
            coverage_pct = n / total_rows * 100
            mean_sst     = float(raw[mask].mean()) if n > 0 else np.nan

            if n < 30:
                print(f"  {region_name}: insufficient data ({n} pts, {coverage_pct:.0f}% coverage)")
                sector_trends[region_name] = dict(
                    slope_per_decade=np.nan, p_value=np.nan,
                    r_squared=np.nan, std_err_decade=np.nan,
                    std_err_raw=np.nan, n=n,
                    mean_sst=mean_sst, coverage_pct=coverage_pct,
                    seasonal_cycle_range=np.nan,
                )
                continue

            # ── 1. Seasonal anomaly ───────────────────────────────────────
            # Build DOY climatology using a 15-day rolling window centred on
            # each day-of-year to smooth noise without over-smoothing the
            # seasonal shape.  Use only the valid observations.
            doy_clim = np.full(367, np.nan)  # index 1–366
            for d in range(1, 367):
                # Window wraps around year-end
                window_doys = set((d + offset - 1) % 366 + 1
                                  for offset in range(-7, 8))
                in_window = mask & np.isin(doy, list(window_doys))
                if in_window.sum() >= 5:
                    doy_clim[d] = raw[in_window].mean()

            # Fill any remaining NaN gaps in climatology by linear interpolation
            valid_d = np.where(~np.isnan(doy_clim[1:]))[0] + 1
            if len(valid_d) > 1:
                doy_clim[1:] = np.interp(
                    np.arange(1, 367),
                    valid_d,
                    doy_clim[valid_d],
                    period=366,
                )
            seasonal_range = float(np.nanmax(doy_clim) - np.nanmin(doy_clim))

            # Subtract climatology to get anomalies
            clim_vals = np.array([doy_clim[d] for d in doy])
            anomaly   = raw - clim_vals          # NaN where raw is NaN

            anom_mask = ~np.isnan(anomaly)
            x = decimal_year[anom_mask]
            y = anomaly[anom_mask]

            if len(x) < 30:
                # Shouldn't happen if raw had >=30 pts, but guard anyway
                sector_trends[region_name] = dict(
                    slope_per_decade=np.nan, p_value=np.nan,
                    r_squared=np.nan, std_err_decade=np.nan,
                    std_err_raw=np.nan, n=n,
                    mean_sst=mean_sst, coverage_pct=coverage_pct,
                    seasonal_cycle_range=seasonal_range,
                )
                continue

            slope, intercept, r_value, p_value_raw, std_err_ols = linregress(x, y)

            # ── 2. Coverage-adjusted uncertainty ─────────────────────────
            # Inflate std_err inversely with sqrt(coverage).
            # At 100% coverage the multiplier is 1.0 (no change).
            # At 25% coverage the multiplier is 2.0 (double the uncertainty).
            coverage_frac  = coverage_pct / 100.0
            cov_multiplier = 1.0 / np.sqrt(max(coverage_frac, 0.01))
            std_err_adj    = std_err_ols * cov_multiplier

            # Recompute p-value from the adjusted std_err using a t-distribution
            df_resid  = len(x) - 2
            t_stat    = slope / std_err_adj if std_err_adj > 0 else np.inf
            p_value   = float(2 * t_dist.sf(abs(t_stat), df=df_resid))

            result = dict(
                slope_per_decade     = slope * 10,
                p_value              = p_value,
                r_squared            = r_value ** 2,
                std_err_decade       = std_err_adj * 10,
                std_err_raw          = std_err_ols * 10,
                n                    = int(n),
                mean_sst             = mean_sst,
                coverage_pct         = coverage_pct,
                seasonal_cycle_range = seasonal_range,
            )
            sector_trends[region_name] = result

            sig = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
            print(f"  {region_name}: {slope*10:+.3f} ±{std_err_adj*10:.3f} °C/dec  "
                  f"p={p_value:.3f}{sig}  r²={r_value**2:.2f}  "
                  f"n={n}  cov={coverage_pct:.0f}%  "
                  f"seas_range={seasonal_range:.1f}°C  "
                  f"cov_mult={cov_multiplier:.2f}x")

        return sector_trends

    except Exception as e:
        import traceback
        print(f"Error calculating trends: {e}")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Dummy data (realistic GAB-like patterns for testing)
# ---------------------------------------------------------------------------

def create_dummy_data(regions):
    """Synthetic trend + metadata that mimics realistic GAB nighttime SST."""
    np.random.seed(42)
    data = {}
    for region_name, bbox in regions.items():
        lon1, lon2, lat1, lat2 = bbox
        center_lat = (min(lat1, lat2) + max(lat1, lat2)) / 2
        center_lon = (min(lon1, lon2) + max(lon1, lon2)) / 2

        # Latitudinal gradient: slight cooling nearshore, warming offshore
        gradient_factor = (center_lat - (-31.0)) / ((-45.0) - (-31.0))
        base_trend = -0.8 + gradient_factor * 2.2
        noise = np.random.normal(0, 0.18)
        slope = base_trend + noise

        # Fake mean SST: warmer in north, cooler south
        mean_sst = 20.0 + (center_lat + 31.0) * 0.5 + np.random.normal(0, 0.3)

        # Fake p-value: bigger trend → more likely significant
        raw_p = max(0.001, 0.5 - abs(slope) * 0.35 + np.random.uniform(-0.1, 0.1))
        r2 = min(0.95, 0.3 + abs(slope) * 0.2 + np.random.uniform(-0.05, 0.05))
        coverage = np.random.uniform(55, 92)

        data[region_name] = dict(
            slope_per_decade=slope,
            p_value=raw_p,
            r_squared=r2,
            std_err_decade=abs(slope) * 0.15 + 0.04,
            n=int(np.random.uniform(150, 800)),
            mean_sst=mean_sst,
            coverage_pct=coverage,
        )
    return data


# ---------------------------------------------------------------------------
# Stipple helper  (draws dots over a patch to signal non-significance)
# ---------------------------------------------------------------------------

def add_stippling(ax, x0, y0, width, height, spacing=0.25, size=1.2, color='#555555'):
    """Overlay a regular dot grid on a rectangle to indicate p >= 0.05."""
    xs = np.arange(x0 + spacing / 2, x0 + width,  spacing)
    ys = np.arange(y0 + spacing / 2, y0 + height, spacing)
    if len(xs) == 0 or len(ys) == 0:
        return
    gx, gy = np.meshgrid(xs, ys)
    ax.scatter(gx.ravel(), gy.ravel(),
               s=size, c=color, alpha=0.55,
               transform=ccrs.PlateCarree(), zorder=5)


# ---------------------------------------------------------------------------
# Main plot
# ---------------------------------------------------------------------------

def plot_gradient_map(title, output_png, regions, colors,
                      csv_path=None, companion='mean_sst', data_dict=None):
    """
    Plot nighttime SST trend map with:
      • colourblind-safe RdBu_r diverging palette
      • stippling for non-significant trends (p >= 0.05)
      • grey hatching for sectors with no data
      • explicit outlier markers beyond colour-scale range
      • r²-modulated border thickness
      • trend label with ± uncertainty (significant sectors only)
      • inset companion map (mean SST or data coverage %)
      • summary stats box

    Parameters
    ----------
    companion : 'mean_sst' | 'coverage' | None
        Which companion metric to show in the inset axes.
    data_dict : dict, optional
        Pre-computed trend dict from calculate_sector_trends(). If supplied,
        csv_path is only used for the data_source label (no re-computation).
    """

    # ---- load / generate data ------------------------------------------------
    if data_dict is not None:
        data_source = (f"VIIRS SST  ({os.path.basename(csv_path)})"
                       if csv_path else "pre-computed")
    elif csv_path and os.path.exists(csv_path):
        print(f"Loading trend data from {csv_path}...")
        data_dict = calculate_sector_trends(csv_path, regions)
        if data_dict is None:
            print("  → failed, falling back to dummy data")
            data_dict = create_dummy_data(regions)
        data_source = f"VIIRS SST  ({os.path.basename(csv_path)})"
    else:
        if csv_path:
            print(f"Data file not found: {csv_path} – using dummy data")
        else:
            print("No CSV supplied – using dummy data")
        data_dict = create_dummy_data(regions)
        data_source = "Synthetic dummy data"

    # ---- map extent ----------------------------------------------------------
    all_lons, all_lats = [], []
    for bbox in regions.values():
        lon1, lon2, lat1, lat2 = bbox
        all_lons += [lon1, lon2]
        all_lats += [lat1, lat2]

    offset = 1.5
    map_ext = [min(all_lons) - offset, max(all_lons) + offset,
               min(all_lats) - offset, max(all_lats) + offset]

    # ---- colour scale --------------------------------------------------------
    # Collect finite slopes only (NaN = no data → rendered separately)
    slopes = []
    for rn in regions:
        d = data_dict.get(rn)
        if d and not np.isnan(d['slope_per_decade']):
            slopes.append(d['slope_per_decade'])

    if slopes:
        # Robust symmetric limits at 98th pctile magnitude
        p98 = np.percentile(np.abs(slopes), 98)
        vmin, vmax = -p98, p98
    else:
        p98 = 1.0
        vmin, vmax = -1.0, 1.0

    # RdBu_r: blue=cold/cooling, red=warm/warming; perceptually uniform + cb-safe
    cmap_trend = plt.cm.RdBu_r
    norm_trend  = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)

    # Companion colour scale
    if companion == 'mean_sst':
        comp_vals = [data_dict[rn]['mean_sst'] for rn in regions
                     if rn in data_dict and data_dict[rn].get('mean_sst') is not None]
        cmap_comp = plt.cm.plasma
        norm_comp = plt.Normalize(vmin=min(comp_vals) if comp_vals else 10,
                                  vmax=max(comp_vals) if comp_vals else 25)
        comp_label = 'Mean SST (°C)'
        comp_key   = 'mean_sst'
    else:
        comp_vals = [data_dict[rn]['coverage_pct'] for rn in regions
                     if rn in data_dict and data_dict[rn].get('coverage_pct') is not None]
        cmap_comp = plt.cm.YlGn
        norm_comp = plt.Normalize(vmin=0, vmax=100)
        comp_label = 'Data coverage (%)'
        comp_key   = 'coverage_pct'

    # ---- figure layout -------------------------------------------------------
    fig = plt.figure(figsize=(16, 11))

    # Main map (left 65%)
    ax = fig.add_axes([0.02, 0.06, 0.60, 0.86],
                      projection=ccrs.PlateCarree())
    ax.set_extent(map_ext, crs=ccrs.PlateCarree())

    # Companion map (top-right)
    ax2 = fig.add_axes([0.65, 0.52, 0.32, 0.40],
                       projection=ccrs.PlateCarree())
    ax2.set_extent(map_ext, crs=ccrs.PlateCarree())

    # Stats box area (bottom-right)
    ax_stats = fig.add_axes([0.65, 0.06, 0.32, 0.42])
    ax_stats.axis('off')

    # ---- base map features (both axes) ---------------------------------------
    land    = cfeature.NaturalEarthFeature('physical', 'land',   '10m',
                                           facecolor='#e8e8e8', edgecolor='none')
    ocean   = cfeature.NaturalEarthFeature('physical', 'ocean',  '10m',
                                           facecolor='#d0e8f0', edgecolor='none')
    lakes   = cfeature.NaturalEarthFeature('physical', 'lakes',  '10m',
                                           facecolor='#d0e8f0', edgecolor='#4488aa',
                                           linewidth=0.5)
    coast   = cfeature.NaturalEarthFeature('physical', 'coastline', '10m',
                                           facecolor='none', edgecolor='#333333',
                                           linewidth=0.8)
    borders = cfeature.NaturalEarthFeature('cultural',
                                           'admin_0_boundary_lines_land', '10m',
                                           facecolor='none', edgecolor='#666666',
                                           linewidth=0.5, linestyle=':')
    for a in (ax, ax2):
        a.add_feature(ocean,   zorder=1)
        a.add_feature(land,    zorder=2)
        a.add_feature(lakes,   zorder=3)
        a.add_feature(coast,   zorder=4)
        a.add_feature(borders, zorder=4)

    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color='gray',
                      alpha=0.5, linestyle='--', zorder=2)
    gl.top_labels = False
    gl.right_labels = False

    gl2 = ax2.gridlines(draw_labels=False, linewidth=0.3, color='gray',
                        alpha=0.4, linestyle='--', zorder=2)

    # ---- draw regions --------------------------------------------------------
    outlier_regions = []   # sectors whose |slope| exceeds colour scale
    sig_count = 0
    ns_count  = 0
    nodata_count = 0

    for region_name, bbox in regions.items():
        lon1, lon2, lat1, lat2 = bbox
        x0     = min(lon1, lon2)
        y0     = min(lat1, lat2)
        width  = abs(lon2 - lon1)
        height = abs(lat2 - lat1)
        cx     = x0 + width  / 2
        cy     = y0 + height / 2

        d = data_dict.get(region_name)

        # ── no data ──────────────────────────────────────────────────────────
        if d is None or np.isnan(d['slope_per_decade']):
            nodata_count += 1
            rect = Rectangle((x0, y0), width, height,
                              linewidth=1, edgecolor='#999999',
                              facecolor='#cccccc', alpha=0.6,
                              hatch='////', transform=ccrs.PlateCarree(), zorder=4)
            ax.add_patch(rect)
            ax.text(cx, cy, region_name, transform=ccrs.PlateCarree(),
                    fontsize=5.5, ha='center', va='center', color='#555555',
                    zorder=6)
            # companion map: also grey
            rect2 = Rectangle((x0, y0), width, height,
                               linewidth=0.5, edgecolor='#aaaaaa',
                               facecolor='#cccccc', alpha=0.5, hatch='////',
                               transform=ccrs.PlateCarree(), zorder=4)
            ax2.add_patch(rect2)
            continue

        slope    = d['slope_per_decade']
        p_val    = d['p_value']
        r2       = d['r_squared']
        std_err  = d['std_err_decade']
        sig      = p_val < 0.05

        if sig:
            sig_count += 1
        else:
            ns_count += 1

        # Detect outlier (strictly beyond the p98 colour scale boundary)
        is_outlier = abs(slope) > p98
        if is_outlier:
            outlier_regions.append((region_name, slope, cx, cy))

        # ── main trend rectangle ─────────────────────────────────────────────
        face_color = cmap_trend(norm_trend(np.clip(slope, vmin, vmax)))
        # r² modulates border thickness: thin = poor fit, thick = good fit
        lw_edge = 0.6 + r2 * 2.2   # 0.6 (r²=0) … 2.8 (r²=1)
        edge_color = colors.get(region_name, '#333333')

        rect = Rectangle((x0, y0), width, height,
                         linewidth=lw_edge, edgecolor=edge_color,
                         facecolor=face_color, alpha=0.85,
                         transform=ccrs.PlateCarree(), zorder=4)
        ax.add_patch(rect)

        # Stipple non-significant sectors
        if not sig:
            add_stippling(ax, x0, y0, width, height,
                          spacing=max(0.18, min(width, height) / 4))

        # ── outlier triangle annotation ───────────────────────────────────────
        if is_outlier:
            marker = '^' if slope > 0 else 'v'
            ax.plot(cx, cy, marker, color='gold', markersize=9,
                    markeredgecolor='black', markeredgewidth=0.6,
                    transform=ccrs.PlateCarree(), zorder=8)

        # ── label: always show name; add trend ± err if significant ──────────
        name_short = region_name
        if sig:
            label = f"{name_short}\n{slope:+.2f}±{std_err:.2f}"
            fc_txt = 'white' if abs(slope) > vmax * 0.6 else '#111111'
            ax.text(cx, cy, label,
                    transform=ccrs.PlateCarree(),
                    fontsize=6, fontweight='bold', ha='center', va='center',
                    color=fc_txt, zorder=7,
                    bbox=dict(boxstyle='round,pad=0.15',
                              facecolor='black' if fc_txt == 'white' else 'white',
                              alpha=0.55, linewidth=0))
        else:
            ax.text(cx, cy, name_short,
                    transform=ccrs.PlateCarree(),
                    fontsize=5.5, ha='center', va='center', color='#222222',
                    zorder=7)

        # ── companion rectangle ───────────────────────────────────────────────
        comp_val = d.get(comp_key)
        if comp_val is not None and not np.isnan(comp_val):
            face2 = cmap_comp(norm_comp(comp_val))
        else:
            face2 = '#cccccc'

        rect2 = Rectangle((x0, y0), width, height,
                           linewidth=0.5, edgecolor='#666666',
                           facecolor=face2, alpha=0.85,
                           transform=ccrs.PlateCarree(), zorder=4)
        ax2.add_patch(rect2)

    # ---- colourbars ----------------------------------------------------------
    # Trend colourbar (horizontal, below main map)
    cax1 = fig.add_axes([0.02, 0.02, 0.60, 0.025])
    sm1  = plt.cm.ScalarMappable(cmap=cmap_trend, norm=norm_trend)
    sm1.set_array([])
    cb1  = fig.colorbar(sm1, cax=cax1, orientation='horizontal')
    cb1.set_label('SST Trend  (°C / decade)', fontsize=10)
    cb1.ax.tick_params(labelsize=8)

    # Companion colourbar (small, beside companion axes)
    cax2 = fig.add_axes([0.975, 0.52, 0.012, 0.40])
    sm2  = plt.cm.ScalarMappable(cmap=cmap_comp, norm=norm_comp)
    sm2.set_array([])
    cb2  = fig.colorbar(sm2, cax=cax2, orientation='vertical')
    cb2.set_label(comp_label, fontsize=8)
    cb2.ax.tick_params(labelsize=7)

    # ---- legend (main map) ---------------------------------------------------
    legend_elements = [
        mpatches.Patch(facecolor='#cccccc', edgecolor='#999999',
                       hatch='////', label='No / insufficient data'),
        mpatches.Patch(facecolor='white', edgecolor='#555555',
                       label='Not significant  (p ≥ 0.05, stippled)'),
        mpatches.Patch(facecolor='white', edgecolor='#555555',
                       linewidth=2.5, label='High r²  (thick border)'),
        plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='gold',
                   markeredgecolor='black', markersize=9,
                   label='Outlier (beyond colour scale)'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=7.5,
              framealpha=0.85, edgecolor='#aaaaaa')

    # ---- stats box -----------------------------------------------------------
    all_slopes = [data_dict[rn]['slope_per_decade'] for rn in regions
                  if rn in data_dict and not np.isnan(data_dict[rn]['slope_per_decade'])]
    all_p      = [data_dict[rn]['p_value'] for rn in regions
                  if rn in data_dict and not np.isnan(data_dict[rn].get('p_value', np.nan))]
    all_r2     = [data_dict[rn]['r_squared'] for rn in regions
                  if rn in data_dict and not np.isnan(data_dict[rn].get('r_squared', np.nan))]
    all_cov    = [data_dict[rn]['coverage_pct'] for rn in regions
                  if rn in data_dict and not np.isnan(data_dict[rn].get('coverage_pct', np.nan))]

    warming  = sum(1 for s in all_slopes if s > 0)
    cooling  = sum(1 for s in all_slopes if s < 0)
    med_slope = np.median(all_slopes) if all_slopes else np.nan

    stats_text = (
        f"SUMMARY  ({data_source})\n"
        f"{'─'*38}\n"
        f"Regions analysed   : {len(regions)}\n"
        f"  ✔ significant (p<0.05)  : {sig_count}\n"
        f"  ~ not significant        : {ns_count}\n"
        f"  ✗ no / insufficient data : {nodata_count}\n\n"
        f"Trend distribution\n"
        f"  warming  (>0)  : {warming} regions\n"
        f"  cooling  (<0)  : {cooling} regions\n"
        f"  median trend   : {med_slope:+.3f} °C/dec\n"
        f"  range          : [{min(all_slopes):+.2f}, {max(all_slopes):+.2f}] °C/dec\n\n"
        f"Model quality (median)\n"
        f"  r²            : {np.median(all_r2):.2f}\n"
        f"  p-value       : {np.median(all_p):.3f}\n\n"
        f"Data coverage (median): {np.median(all_cov):.0f}%\n"
    ) if all_slopes else "No data available."

    ax_stats.text(0.04, 0.97, stats_text,
                  transform=ax_stats.transAxes,
                  fontsize=8.5, va='top', ha='left',
                  fontfamily='monospace',
                  bbox=dict(boxstyle='round,pad=0.6',
                            facecolor='#fffef0', edgecolor='#ccbb88',
                            linewidth=1.2))

    # ---- titles --------------------------------------------------------------
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
    ax2.set_title(comp_label, fontsize=9, fontweight='bold', pad=6)

    # ---- save / show ---------------------------------------------------------
    plt.savefig(output_png, dpi=300, bbox_inches='tight',
                facecolor='white')
    print(f"\nMap saved → {output_png}")


# ---------------------------------------------------------------------------
# Explainer report
# ---------------------------------------------------------------------------

def print_explainer(title, data_dict, regions, csv_path=None):
    """
    Print a rich plain-text analysis report to stdout.

    Designed to be copy-pasted back to an LLM for interpretation.
    Covers: dataset overview, per-region table sorted by trend magnitude,
    spatial pattern commentary hooks, data quality summary, and
    seasonal decomposition if enough data exists.
    """
    sep  = "=" * 72
    sep2 = "-" * 72

    # ---- gather valid records ------------------------------------------------
    records = []
    for rn, bbox in regions.items():
        lon1, lon2, lat1, lat2 = bbox
        cx = (min(lon1, lon2) + max(lon1, lon2)) / 2
        cy = (min(lat1, lat2) + max(lat1, lat2)) / 2
        d  = data_dict.get(rn, {})
        records.append(dict(
            name         = rn,
            center_lon   = cx,
            center_lat   = cy,
            slope              = d.get('slope_per_decade',      np.nan),
            p_value            = d.get('p_value',                np.nan),
            r_squared          = d.get('r_squared',               np.nan),
            std_err            = d.get('std_err_decade',          np.nan),
            std_err_raw        = d.get('std_err_raw',             np.nan),
            n                  = d.get('n',                       0),
            mean_sst           = d.get('mean_sst',                np.nan),
            coverage_pct       = d.get('coverage_pct',            np.nan),
            seasonal_cycle_range = d.get('seasonal_cycle_range',  np.nan),
        ))

    valid   = [r for r in records if not np.isnan(r['slope'])]
    sig     = [r for r in valid   if r['p_value'] < 0.05]
    insig   = [r for r in valid   if r['p_value'] >= 0.05]
    nodata  = [r for r in records if np.isnan(r['slope'])]

    slopes_sig = [r['slope'] for r in sig]

    # ---- header --------------------------------------------------------------
    print()
    print(sep)
    print(f"  NIGHTTIME SST TREND ANALYSIS — EXPLAINER REPORT")
    print(f"  {title}")
    if csv_path:
        print(f"  Source : {csv_path}")
    print(sep)

    # ---- methodology note ----------------------------------------------------
    print()
    print("METHODOLOGY")
    print(sep2)
    print("  Trends are computed on SEASONAL ANOMALIES, not raw SST.")
    print("  A 15-day rolling day-of-year climatology is subtracted from each")
    print("  region before regression, removing the seasonal cycle so that")
    print("  uneven cloud-free sampling across seasons cannot bias the trend.")
    print()
    print("  Uncertainty (std_err) is COVERAGE-ADJUSTED:")
    print("  std_err_adj = std_err_OLS / sqrt(coverage_fraction)")
    print("  At 25% coverage the reported uncertainty is 2x the raw OLS value.")
    print("  The slope itself is unchanged; only confidence intervals widen.")
    print("  p-values are recomputed from the adjusted std_err.")
    print()
    print("  The table shows both ±adj (coverage-adjusted) and ±raw (OLS only)")
    print("  so you can see how much low coverage is inflating uncertainty.")

    # ---- dataset overview ----------------------------------------------------
    print()
    print("DATASET OVERVIEW")
    print(sep2)

    if valid:
        date_range_note = ""
        if csv_path and os.path.exists(csv_path):
            try:
                idx = pd.read_csv(csv_path, index_col=0, usecols=[0]).index
                idx = pd.to_datetime(idx.astype(str), format="%Y%m%d")
                date_range_note = (f"  Date range      : {idx.min().date()} → {idx.max().date()}"
                                   f"  ({(idx.max()-idx.min()).days // 365} yr"
                                   f" {((idx.max()-idx.min()).days % 365) // 30} mo)\n"
                                   f"  Total rows      : {len(idx)} daily observations\n")
            except Exception:
                pass
        print(date_range_note, end="")

    all_slopes = [r['slope'] for r in valid]
    all_cov    = [r['coverage_pct'] for r in valid if not np.isnan(r['coverage_pct'])]
    all_r2     = [r['r_squared']    for r in valid if not np.isnan(r['r_squared'])]
    all_n      = [r['n']            for r in valid]

    print(f"  Regions total   : {len(records)}")
    print(f"    significant (p<0.05) : {len(sig)}")
    print(f"    not significant      : {len(insig)}")
    print(f"    no/insufficient data : {len(nodata)}")
    if all_slopes:
        print(f"  Trend range     : {min(all_slopes):+.3f} to {max(all_slopes):+.3f} °C/decade")
        print(f"  Median trend    : {np.median(all_slopes):+.3f} °C/decade")
        print(f"  Mean trend      : {np.mean(all_slopes):+.3f} °C/decade")
        warming_sig = sum(1 for r in sig if r['slope'] > 0)
        cooling_sig = sum(1 for r in sig if r['slope'] < 0)
        print(f"  Significant warming regions  : {warming_sig}")
        print(f"  Significant cooling regions  : {cooling_sig}")
    if all_cov:
        print(f"  Median coverage : {np.median(all_cov):.0f}%  "
              f"(range {min(all_cov):.0f}–{max(all_cov):.0f}%)")
    if all_r2:
        print(f"  Median r²       : {np.median(all_r2):.3f}  "
              f"(range {min(all_r2):.3f}–{max(all_r2):.3f})")
    if all_n:
        print(f"  Median obs/region: {int(np.median(all_n))}  "
              f"(range {min(all_n)}–{max(all_n)})")

    # ---- per-region table ----------------------------------------------------
    print()
    print("PER-REGION RESULTS  (sorted by trend magnitude, significant first)")
    print(sep2)
    hdr = f"  {'Region':<12}  {'Lat':>7}  {'Lon':>7}  {'Trend':>9}  {'±adj':>7}  {'±raw':>7}  "
    hdr += f"{'p':>7}  {'sig':>4}  {'r²':>5}  {'SeasRng':>8}  {'MeanSST':>8}  {'cov%':>5}  {'n':>5}"
    print(hdr)
    print("  " + "-" * 116)

    def sig_stars(p):
        if np.isnan(p): return "  ?"
        if p < 0.001:   return "***"
        if p < 0.01:    return " **"
        if p < 0.05:    return "  *"
        return "  ~"

    # significant first, then insig, sorted by |slope| descending within each group
    ordered = (sorted(sig,   key=lambda r: abs(r['slope']), reverse=True) +
               sorted(insig, key=lambda r: abs(r['slope']), reverse=True) +
               nodata)

    for r in ordered:
        slope_s   = f"{r['slope']:+.3f}"         if not np.isnan(r['slope'])             else "  n/a "
        err_adj_s = f"±{r['std_err']:.3f}"       if not np.isnan(r['std_err'])           else "  n/a "
        err_raw_s = f"±{r['std_err_raw']:.3f}"   if not np.isnan(r['std_err_raw'])       else "  n/a "
        p_s       = f"{r['p_value']:.4f}"         if not np.isnan(r['p_value'])           else "  n/a "
        r2_s      = f"{r['r_squared']:.3f}"       if not np.isnan(r['r_squared'])         else " n/a "
        seas_s    = f"{r['seasonal_cycle_range']:.1f}°" if not np.isnan(r['seasonal_cycle_range']) else "  n/a"
        sst_s     = f"{r['mean_sst']:.2f}"         if not np.isnan(r['mean_sst'])         else "  n/a "
        cov_s     = f"{r['coverage_pct']:.0f}"     if not np.isnan(r['coverage_pct'])     else "n/a"
        print(f"  {r['name']:<12}  {r['center_lat']:>7.2f}  {r['center_lon']:>7.2f}  "
              f"{slope_s:>9}  {err_adj_s:>7}  {err_raw_s:>7}  "
              f"{p_s:>7}  {sig_stars(r['p_value']):>4}  "
              f"{r2_s:>5}  {seas_s:>8}  {sst_s:>8}  {cov_s:>5}  {r['n']:>5}")

    # ---- spatial pattern summary ---------------------------------------------
    print()
    print("SPATIAL PATTERNS")
    print(sep2)

    if valid:
        # North vs south split at median latitude
        lats = [r['center_lat'] for r in valid]
        mid_lat = np.median(lats)
        north = [r for r in valid if r['center_lat'] > mid_lat]
        south = [r for r in valid if r['center_lat'] <= mid_lat]
        if north and south:
            mn = np.mean([r['slope'] for r in north])
            ms = np.mean([r['slope'] for r in south])
            print(f"  Latitudinal split at {mid_lat:.1f}°:")
            print(f"    North (>{mid_lat:.1f}°)  mean trend : {mn:+.3f} °C/decade  "
                  f"(n={len(north)} regions)")
            print(f"    South (<{mid_lat:.1f}°) mean trend : {ms:+.3f} °C/decade  "
                  f"(n={len(south)} regions)")
            diff = ms - mn
            direction = "stronger warming" if diff > 0 else "stronger cooling"
            print(f"    South–North difference : {diff:+.3f} °C/decade ({direction} in south)")

        # East vs west split at median longitude
        lons = [r['center_lon'] for r in valid]
        mid_lon = np.median(lons)
        west = [r for r in valid if r['center_lon'] <= mid_lon]
        east = [r for r in valid if r['center_lon'] > mid_lon]
        if west and east:
            mw = np.mean([r['slope'] for r in west])
            me = np.mean([r['slope'] for r in east])
            print(f"  Longitudinal split at {mid_lon:.1f}°E:")
            print(f"    West (<{mid_lon:.1f}°E) mean trend : {mw:+.3f} °C/decade  "
                  f"(n={len(west)} regions)")
            print(f"    East (>{mid_lon:.1f}°E) mean trend : {me:+.3f} °C/decade  "
                  f"(n={len(east)} regions)")

        # Strongest signals
        if sig:
            top_warm = max(sig, key=lambda r: r['slope'])
            top_cool = min(sig, key=lambda r: r['slope'])
            print(f"  Strongest significant warming : {top_warm['name']}  "
                  f"{top_warm['slope']:+.3f} °C/dec  "
                  f"({top_warm['center_lat']:.1f}°, {top_warm['center_lon']:.1f}°E)")
            print(f"  Strongest significant cooling : {top_cool['name']}  "
                  f"{top_cool['slope']:+.3f} °C/dec  "
                  f"({top_cool['center_lat']:.1f}°, {top_cool['center_lon']:.1f}°E)")

        # Correlation: trend vs latitude and vs mean SST
        lat_arr  = np.array([r['center_lat'] for r in valid])
        sst_arr  = np.array([r['mean_sst']   for r in valid if not np.isnan(r['mean_sst'])])
        slp_arr  = np.array([r['slope']       for r in valid])
        slp_sst  = np.array([r['slope'] for r in valid if not np.isnan(r['mean_sst'])])

        if len(lat_arr) >= 4:
            from scipy.stats import pearsonr
            r_lat, p_lat = pearsonr(lat_arr, slp_arr)
            print(f"  Trend vs latitude correlation : r={r_lat:+.3f}  p={p_lat:.4f}"
                  f"  ({'significant' if p_lat < 0.05 else 'not significant'})")
        if len(sst_arr) >= 4:
            r_sst, p_sst = pearsonr(sst_arr, slp_sst)
            print(f"  Trend vs mean SST correlation : r={r_sst:+.3f}  p={p_sst:.4f}"
                  f"  ({'significant' if p_sst < 0.05 else 'not significant'})")

    # ---- seasonal decomposition (if raw CSV available) -----------------------
    if csv_path and os.path.exists(csv_path):
        print()
        print("SEASONAL BREAKDOWN  (mean SST by season, averaged across all regions)")
        print(sep2)
        try:
            df = pd.read_csv(csv_path, index_col=0)
            df.index = pd.to_datetime(df.index.astype(str), format="%Y%m%d")
            df = df.sort_index()
            region_cols = [c for c in regions.keys() if c in df.columns]

            # Australian seasons
            season_map = {12: "Summer", 1: "Summer", 2: "Summer",
                          3:  "Autumn", 4: "Autumn", 5: "Autumn",
                          6:  "Winter", 7: "Winter", 8: "Winter",
                          9:  "Spring",10: "Spring",11: "Spring"}
            df['season'] = df.index.month.map(season_map)
            df['year']   = df.index.year

            season_means = (df[region_cols + ['season']]
                            .groupby('season')[region_cols]
                            .mean()
                            .mean(axis=1)
                            .reindex(['Summer', 'Autumn', 'Winter', 'Spring']))

            for season, val in season_means.items():
                bar = "█" * int(max(0, val - season_means.min()) / max(0.01, season_means.max() - season_means.min()) * 20)
                print(f"  {season:<8} : {val:5.2f} °C  {bar}")

            # Per-season trend (early vs late years)
            years = sorted(df['year'].unique())
            if len(years) >= 6:
                mid_year = years[len(years) // 2]
                early = df[df['year'] <  mid_year][region_cols + ['season']]
                late  = df[df['year'] >= mid_year][region_cols + ['season']]
                print(f"\n  Early period (<{mid_year}) vs late period (≥{mid_year}) "
                      f"seasonal mean SST shift:")
                for season in ['Summer', 'Autumn', 'Winter', 'Spring']:
                    e = early[early['season'] == season][region_cols].values
                    l = late[ late[ 'season'] == season][region_cols].values
                    e_mean = np.nanmean(e) if len(e) > 0 else np.nan
                    l_mean = np.nanmean(l) if len(l) > 0 else np.nan
                    if not (np.isnan(e_mean) or np.isnan(l_mean)):
                        delta = l_mean - e_mean
                        arrow = "↑" if delta > 0 else "↓"
                        print(f"    {season:<8}: {e_mean:.2f} → {l_mean:.2f} °C  "
                              f"({arrow}{abs(delta):.2f} °C)")
        except Exception as e:
            print(f"  (seasonal breakdown unavailable: {e})")

    # ---- data quality notes --------------------------------------------------
    print()
    print("DATA QUALITY NOTES")
    print(sep2)
    low_cov  = [r for r in valid if r['coverage_pct'] < 40]
    low_r2   = [r for r in sig   if r['r_squared'] < 0.1]
    high_err = [r for r in sig   if not np.isnan(r['std_err']) and
                abs(r['std_err']) > abs(r['slope']) * 0.5]

    if low_cov:
        names = ", ".join(r['name'] for r in low_cov)
        print(f"  Low coverage (<40%): {names}")
        print(f"    → cloud/gap-prone; trends may be biased toward clear-sky conditions")
    if low_r2:
        names = ", ".join(r['name'] for r in low_r2)
        print(f"  Significant but low r² (<0.1): {names}")
        print(f"    → linear model explains little variance; trend is real but noisy")
    if high_err:
        names = ", ".join(r['name'] for r in high_err)
        print(f"  High uncertainty (std_err > 50% of slope): {names}")
        print(f"    → treat these trend estimates with caution")
    if nodata:
        names = ", ".join(r['name'] for r in nodata)
        print(f"  No data: {names}")
    if not any([low_cov, low_r2, high_err, nodata]):
        print("  No significant data quality concerns flagged.")

    print()
    print(sep)
    print("  END OF EXPLAINER REPORT — paste above to an LLM for interpretation")
    print(sep)
    print()

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot nighttime SST trend map with companion diagnostics'
    )
    parser.add_argument('title',        type=str, help='Map title')
    parser.add_argument('regions_json', type=str, help='Path to regions JSON')
    parser.add_argument('output_png',   type=str, help='Output PNG path')
    parser.add_argument('--csv',        type=str, default=None,
                        help='CSV with per-region SST time series')
    parser.add_argument('--companion',  type=str, default='mean_sst',
                        choices=['mean_sst', 'coverage'],
                        help='Companion inset metric (default: mean_sst)')
    parser.add_argument('--explainer',  action='store_true',
                        help='Print a detailed plain-text analysis report to stdout')

    args = parser.parse_args()

    regions, colors = get_regions(args.regions_json)

    # Always compute trends (needed for both map and explainer)
    if args.csv and os.path.exists(args.csv):
        data_dict = calculate_sector_trends(args.csv, regions)
        if data_dict is None:
            print("Warning: trend calculation failed, using dummy data")
            data_dict = create_dummy_data(regions)
    else:
        data_dict = create_dummy_data(regions)

    plot_gradient_map(args.title, args.output_png, regions, colors,
                      csv_path=args.csv, companion=args.companion)

    if args.explainer:
        print_explainer(args.title, data_dict, regions, csv_path=args.csv)
