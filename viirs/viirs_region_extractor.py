#!/usr/bin/env python3
"""
Extract data for specified regions from NetCDF files.
"""
import argparse
import csv
import signal
import sys
import logging

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import numpy as np
import netCDF4 as nc
from tqdm import tqdm
from viirs_regions import get_regions

LOG_LEVEL = logging.INFO

# Flag to handle Ctrl+C
interrupted = False

# “4 km resolution” means each pixel represents roughly 4 km × 4 km on the ground.

# minimum number of pixels to capture
MIN_VALID_PIXELS = 30

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global interrupted
    print("\n\nInterrupted! Saving progress...", file=sys.stderr)
    interrupted = True

def parse_date_from_filename(filename: str) -> Optional[str]:
    """Extract date from filename like SNPP_VIIRS.20120101.L3m.DAY.CHL.chlor_a.4km.nc
    or JPSS1_VIIRS.20171213.L3m.DAY.CHL.chlor_a.4km.nc"""
    import re
    match = re.search(r'(?:SNPP|JPSS1)_VIIRS\.(\d{8})\.', filename)
    if match:
        return match.group(1)
    return None

def get_processed_dates(csv_path: Path) -> Set[str]:
    """Read existing CSV and return set of dates already processed."""
    if not csv_path.exists():
        return set()

    processed = set()
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['date']:
                processed.add(row['date'])

    return processed

def detect_viirs_variables(dataset):
    """Auto-detect VIIRS variable names for chlorophyll-a."""
    variables = list(dataset.variables.keys())

    sst_candidates = ['sst', 'sst4', 'sea_surface_temperature', 'SST', 'SST4']
    chlor_candidates = ['chlor_a', 'chlorophyll_a', 'CHL', 'chl']
    lat_candidates = ['lat', 'latitude', 'Latitude']
    lon_candidates = ['lon', 'longitude', 'Longitude']
    qual_candidates = ['qual_sst', 'quality_level', 'sst_quality', 'quality']

    chlor_var = next((c for c in chlor_candidates if c in variables), None)
    lat_var = next((c for c in lat_candidates if c in variables), None)
    lon_var = next((c for c in lon_candidates if c in variables), None)
    sst_var = next((c for c in sst_candidates if c in variables), None)
    qual_var = next((c for c in qual_candidates if c in variables), None)

    if (chlor_var is not None):
        valid_range = (0.01, 50)    # 0.01-100 mg/m3
        data_var = chlor_var
    else:
        valid_range = (-5.0, 60)  # SST range in Celsius
        data_var = sst_var

    return data_var, lat_var, lon_var, valid_range, qual_var

def determine_viirs_scaling(dataset, data_var, valid_range):
    """Determine if VIIRS data needs scaling based on data analysis."""
    try:
        data = dataset.variables[data_var][:]

        # Get sample of valid data
        if hasattr(data, 'mask'):
            valid_sample = data[~data.mask]
        else:
            fill_value = getattr(dataset.variables[data_var], '_FillValue', -32767)
            valid_sample = data[data != fill_value]

        if len(valid_sample) == 0:
            return False

        # Sample for efficiency
        sample_size = min(10000, len(valid_sample))
        sample = valid_sample.flatten()[:sample_size]
        raw_mean = float(np.mean(sample))

        # If raw values are reasonable (0-100 mg/mÂ³), don't scale
        if valid_range[0] <= raw_mean <= valid_range[1]:
            return False

        # Test if scaling brings values into range
        data_variable = dataset.variables[data_var]
        scale_factor = getattr(data_variable, 'scale_factor', 1.0)
        add_offset = getattr(data_variable, 'add_offset', 0.0)
        scaled_sample = sample * scale_factor + add_offset
        scaled_mean = float(np.mean(scaled_sample))

        return valid_range[0] <= scaled_mean <= valid_range[1]
    except Exception:
        return False

def extract_region_mean(dataset, bbox: List[float]) -> Optional[float]:
    """
    Extract mean chlorophyll-a for a region, applying quality flags.
    Handles both Northern and Southern Hemisphere coordinates correctly.

    Args:
        dataset: NetCDF dataset
        bbox: [min_lon, max_lon, lat1, lat2] where lat1 and lat2 can be in any order

    Returns:
        Mean chlorophyll-a value or None if no valid data
    """
    lon1, lon2, lat1, lat2 = bbox

    # Ensure proper min/max ordering (handles Southern Hemisphere)
    min_lon = min(lon1, lon2)
    max_lon = max(lon1, lon2)
    min_lat = min(lat1, lat2)  # Most negative (southernmost)
    max_lat = max(lat1, lat2)  # Least negative (northernmost)

    try:
        # Auto-detect variables
        data_var, lat_var, lon_var, valid_range, qual_var = detect_viirs_variables(dataset)
        if not all([data_var, lat_var, lon_var]):
            logger.debug("no variables")
            return None

        # Load coordinate and data arrays
        lat = dataset.variables[lat_var][:]
        lon = dataset.variables[lon_var][:]
        data = dataset.variables[data_var][:]

        # Load quality data if available
        qual_data = None
        if qual_var and qual_var in dataset.variables:
            qual_data = dataset.variables[qual_var][:]
            logger.debug(f"Using quality variable: {qual_var}")

        # Get metadata for quality filtering
        data_variable = dataset.variables[data_var]
        fill_value = getattr(data_variable, '_FillValue', -32767)

        valid_min = valid_range[0]
        valid_max = valid_range[1]
        if hasattr(data_variable, "valid_min"):
            value = getattr(data_variable, 'valid_min')
            if (value > valid_min):
                valid_min = value
        if hasattr(data_variable, "valid_max"):
            value = getattr(data_variable, 'valid_max')
            if (value < valid_max):
                valid_max = value

        # Determine if scaling is needed
        use_scaling = determine_viirs_scaling(dataset, data_var, valid_range)
        if use_scaling:
            scale_factor = getattr(data_variable, 'scale_factor', 1.0)
            add_offset = getattr(data_variable, 'add_offset', 0.0)
        else:
            scale_factor = 1.0
            add_offset = 0.0

        # Handle coordinate systems
        if lat.ndim == 1 and lon.ndim == 1:
            # 1D coordinates - convert longitude from 0-360 to -180-180 if needed
            if np.any(lon > 180):
                lon = np.where(lon > 180, lon - 360, lon)

            # Find indices within region
            lat_mask = (lat >= min_lat) & (lat <= max_lat)
            lon_mask = (lon >= min_lon) & (lon <= max_lon)
            lat_inds = np.where(lat_mask)[0]
            lon_inds = np.where(lon_mask)[0]

            if len(lat_inds) == 0 or len(lon_inds) == 0:
                logger.debug(f"region error {len(lat_inds)}")
                return None

            # Extract data slice
            if data.ndim == 3:  # Has time dimension
                data_slice = data[0, lat_inds.min():lat_inds.max()+1,
                                  lon_inds.min():lon_inds.max()+1]
                if qual_data is not None:
                    qual_slice = qual_data[0, lat_inds.min():lat_inds.max()+1,
                                          lon_inds.min():lon_inds.max()+1]
            else:
                data_slice = data[lat_inds.min():lat_inds.max()+1,
                                       lon_inds.min():lon_inds.max()+1]
                if qual_data is not None:
                    qual_slice = qual_data[lat_inds.min():lat_inds.max()+1,
                                          lon_inds.min():lon_inds.max()+1]

        elif lat.ndim == 2 and lon.ndim == 2:
            # 2D coordinates
            if np.any(lon > 180):
                lon = np.where(lon > 180, lon - 360, lon)

            spatial_mask = ((lat >= min_lat) & (lat <= max_lat) &
                          (lon >= min_lon) & (lon <= max_lon))

            if data.ndim == 3:
                data_slice = data[0, :, :][spatial_mask]
                if qual_data is not None:
                    qual_slice = qual_data[0, :, :][spatial_mask]
            else:
                data_slice = data[spatial_mask]
                if qual_data is not None:
                    qual_slice = qual_data[spatial_mask]
        else:
            logger.debug(f"unexpected dimension {lat.ndim} {lon.ndim}")
            return None

        # Handle masked arrays
        if hasattr(data_slice, 'mask'):
            data_slice = data_slice.compressed()
            if qual_data is not None and hasattr(qual_slice, 'mask'):
                qual_slice = qual_slice.compressed()

        # Flatten if multidimensional
        data_slice = data_slice.flatten() if data_slice.ndim > 1 else data_slice

        # Apply quality filters
        valid_mask = np.ones(data_slice.shape, dtype=bool)

        # Filter fill values
        if fill_value is not None:
            valid_mask &= (data_slice != fill_value)

        # Filter non-finite and zero values
        valid_mask &= np.isfinite(data_slice) & (data_slice != 0)

        # Apply SST quality filter if available
        if qual_data is not None and len(qual_slice) == len(data_slice):
            # Common VIIRS quality levels: 0=best, 1=good, 2=questionable, 3=bad, 4=worst
            # Keep only best and good quality data
            quality_mask = (qual_slice <= 1)  # Keep quality 0 and 1
            valid_mask &= quality_mask
            logger.debug(f"Quality filter kept {np.sum(quality_mask)} of {len(quality_mask)} pixels")

        # print (f"ndim {data_slice.ndim}")
        valid_raw_data = data_slice[valid_mask] if data_slice.ndim > 0 else np.array([data_slice])[valid_mask]

        if len(valid_raw_data) < MIN_VALID_PIXELS:
            logger.debug(f"Too few raw pixels {len(valid_raw_data)}")
            return None

        # Apply scaling and final validation
        scaled_data = valid_raw_data * scale_factor + add_offset

        # Final quality filters for chlorophyll-a
        # Valid range: 0.01 to 100 mg/mÂ³ (remove negatives and extreme outliers)
        final_valid = ((scaled_data >= valid_min) & (scaled_data <= valid_max) &
                      np.isfinite(scaled_data))

        final_data = scaled_data[final_valid]

        if len(final_data) < MIN_VALID_PIXELS:
            logger.debug(f"Too few valid pixels {len(valid_raw_data)}")
            return None

        return float(np.mean(final_data))

    except Exception as e:
        print(f"Error extracting region {bbox}: {e}", file=sys.stderr)
        return None

def process_file(regions, nc_path: Path) -> Optional[Dict[str, float]]:
    """
    Process a single NetCDF file and extract regional means.

    Returns:
        Dictionary with region names as keys and mean chlorophyll as values,
        or None if file cannot be processed
    """
    try:
        with nc.Dataset(nc_path, 'r') as dataset:
            result = {}
            for region_name, bbox in regions.items():
                mean_val = extract_region_mean(dataset, bbox)
                result[region_name] = mean_val
            return result
    except Exception as e:
        print(f"Error processing {nc_path.name}: {e}", file=sys.stderr)
        return None

def file_name_sort(name):
    return parse_date_from_filename(name.name)

def filter_by_date(all_files, start_date):
    result = [f for f in all_files if parse_date_from_filename(f.name) >= start_date]
    return result

def main():
    global interrupted

    parser = argparse.ArgumentParser(
        description='Extract regional chlorophyll-a data from NetCDF files'
    )
    parser.add_argument(
        'regions_json',
        type=str,
        help='The regions to inspect'
    )
    parser.add_argument(
        'input_folder',
        type=str,
        help='Folder containing NetCDF files'
    )
    parser.add_argument(
        'output_csv',
        type=str,
        help='Output CSV file path'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date'
    )

    args = parser.parse_args()

    # Setup
    input_folder = Path(args.input_folder)
    output_csv = Path(args.output_csv)
    start_date = args.start_date

    if not input_folder.exists():
        print(f"Error: Input folder {input_folder} does not exist", file=sys.stderr)
        sys.exit(1)

    regions, colors = get_regions(args.regions_json)

    # Column names for CSV
    column_names = ['date'] + list(regions.keys())

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Get list of NetCDF files (both SNPP and JPSS-1)
    all_files = list(input_folder.glob('*_VIIRS.*.nc'))
    nc_files = sorted(all_files, key=file_name_sort, reverse=False)

    if start_date is not None:
        nc_files = filter_by_date(nc_files, start_date)

    if not nc_files:
        print(f"Error: No VIIRS NetCDF files found in {input_folder}", file=sys.stderr)
        print(f"Looking for: SNPP_VIIRS.*.nc or JPSS1_VIIRS.*.nc", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(nc_files)} VIIRS NetCDF files")

    # Count by satellite
    snpp_count = sum(1 for f in nc_files if 'SNPP' in f.name)
    jpss1_count = sum(1 for f in nc_files if 'JPSS1' in f.name)
    if snpp_count > 0:
        print(f"  - SNPP (Suomi NPP): {snpp_count} files")
    if jpss1_count > 0:
        print(f"  - JPSS-1 (NOAA-20): {jpss1_count} files")

    # Check for existing progress
    processed_dates = get_processed_dates(output_csv)

    if processed_dates:
        print(f"Resuming: {len(processed_dates)} dates already processed")

    # Determine if we need to write header
    write_header = not output_csv.exists() or output_csv.stat().st_size == 0

    # Open CSV for appending
    with open(output_csv, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=column_names)

        if write_header:
            writer.writeheader()

        # Process files
        processed_count = 0
        skipped_count = len(processed_dates)

        for nc_path in tqdm(nc_files, desc="Processing files", unit="file"):
            if interrupted:
                break

            # Extract date from filename
            date_str = parse_date_from_filename(nc_path.name)
            if not date_str:
                continue

            # Skip if already processed
            if date_str in processed_dates:
                continue

            # Process file
            region_data = process_file(regions, nc_path)

            if region_data is not None:
                # Write row to CSV
                row = {'date': date_str}
                row.update(region_data)
                writer.writerow(row)
                csvfile.flush()  # Ensure data is written to disk
                processed_count += 1
            else:
                # Write row with date but empty values
                row = {'date': date_str}
                for region in regions.keys():
                    row[region] = None
                writer.writerow(row)
                csvfile.flush()

        # Final summary
        total_in_csv = len(processed_dates) + processed_count
        print(f"\n{'='*60}")
        print(f"Processing Summary:")
        print(f"{'='*60}")
        print(f"New files processed: {processed_count}")
        print(f"Previously processed: {skipped_count}")
        print(f"Total entries in CSV: {total_in_csv}")
        print(f"Output file: {output_csv}")
        print(f"{'='*60}")

    if interrupted:
        print(f"\nProcessing interrupted. Processed {processed_count} new files.")
        print(f"Total in CSV: {len(processed_dates) + processed_count}")
        print("Run again to continue from where you left off.")
        sys.exit(130)  # Standard exit code for SIGINT
    else:
        print(f"\nComplete! Output saved to: {output_csv}")

if __name__ == '__main__':
    main()
