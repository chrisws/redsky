#!/usr/bin/env python3
"""
Convert wide-format chlorophyll CSV data to embedded JSON for HTML.

Input CSV format expected:
date,region1,region2,region3
20240101,0.45,0.52,0.48
20240102,0.46,,0.49
...

Output: JavaScript code to embed in HTML with region metadata
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

def get_regions(path):
    with open(path, "r") as file:
        regions_data = json.load(file)

    regions = {}
    colors = {}
    for region_name, region in regions_data.items():
        regions[region_name] = {}
        colors[region_name] = {}
        for key, value in region.items():
            if (key == 'box'):
                regions[region_name] = value
            else:
                colors[region_name] = value
    return [regions, colors]

def format_date(date_str: str) -> str:
    """Convert YYYYMMDD to YYYY-MM-DD format"""
    if len(date_str) == 8:
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def bbox_to_center(bbox: List[float]) -> List[float]:
    """
    Calculate center point from bounding box.
    
    Args:
        bbox: [lon1, lon2, lat1, lat2]
        
    Returns:
        [lat, lon] center point
    """
    lon1, lon2, lat1, lat2 = bbox
    center_lat = (lat1 + lat2) / 2
    center_lon = (lon1 + lon2) / 2
    return [center_lat, center_lon]


def convert_csv_to_embedded_json(
    csv_path: str, 
    regions_json: str = None,
    output_html: str = None
) -> str:
    """
    Convert wide-format CSV to JavaScript data for HTML embedding.
    
    Args:
        csv_path: Path to input CSV file
        regions_json: Path to regions JSON file with bbox and colors
        output_html: Path to base HTML file to embed data into (optional)
        
    Returns:
        JavaScript code string
    """
    data_array = []
    regions_list = []
    dates = []
    
    # Load region metadata if provided
    region_bboxes = {}
    region_colors = {}
    region_coordinates = {}
    
    if regions_json and Path(regions_json).exists():
        print(f"Loading region metadata from {regions_json}")
        region_bboxes, region_colors = get_regions(regions_json)
        
        # Calculate center coordinates for map
        for region_name, bbox in region_bboxes.items():
            region_coordinates[region_name] = bbox_to_center(bbox)
        
        print(f"Loaded {len(region_bboxes)} regions with coordinates and colors")
    
    # Read CSV data
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        # First column is date, rest are regions
        date_col = fieldnames[0]
        regions_list = [col for col in fieldnames[1:]]
        
        print(f"Found {len(regions_list)} regions in CSV: {', '.join(regions_list)}")
        
        for row in reader:
            date_raw = row[date_col]
            date_formatted = format_date(date_raw)
            dates.append(date_formatted)
            
            row_data = {"date": date_formatted}
            for region in regions_list:
                value_str = row[region]
                # Parse value (handle empty, None, NaN)
                try:
                    value = float(value_str) if value_str and value_str.strip() else None
                except (ValueError, TypeError):
                    value = None
                row_data[region] = value
            
            data_array.append(row_data)
    
    # Calculate statistics
    total_points = sum(1 for row in data_array for region in regions_list if row[region] is not None)
    
    # Build region metadata for JavaScript
    regions_metadata = {}
    for region in regions_list:
        region_meta = {"name": region}
        
        # Add bbox if available
        if region in region_bboxes:
            region_meta["bbox"] = region_bboxes[region]
        
        # Add color if available
        if region in region_colors:
            region_meta["color"] = region_colors[region]
        
        # Add coordinates if available
        if region in region_coordinates:
            region_meta["coordinates"] = region_coordinates[region]
        
        regions_metadata[region] = region_meta
    
    # Build metadata
    metadata = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "date_range": {
            "start": dates[0] if dates else None,
            "end": dates[-1] if dates else None
        },
        "regions": regions_list,
        "regions_metadata": regions_metadata,
        "total_dates": len(dates),
        "total_regions": len(regions_list),
        "data_points": total_points,
        "source": "NOAA MSL12 VIIRS Merged SNPP+NOAA-20 NRT",
        "variable": "Chlorophyll-a Concentration",
        "units": "mg/m³"
    }
    
    # Create JSON structure
    json_data = {
        "metadata": metadata,
        "data": data_array
    }
    
    # Generate JavaScript code
    js_code = f"const CHLOROPHYLL_DATA = {json.dumps(json_data, indent=2)};"
    
    print(f"\n✓ Processed {len(dates)} dates")
    print(f"  Date range: {dates[0]} to {dates[-1]}")
    print(f"  Regions: {len(regions_list)}")
    print(f"  Total data points: {total_points}")
    if region_coordinates:
        print(f"  Regions with map coordinates: {len(region_coordinates)}")
    if region_colors:
        print(f"  Regions with custom colors: {len(region_colors)}")
    
    # Save as standalone JS file
    js_path = 'chlorophyll_data.js'
    with open(js_path, 'w') as f:
        f.write(js_code)
        print(f"\n✓ Created {js_path}")
        
    return js_code


def main():
    if len(sys.argv) < 2:
        print("Usage: python csv_to_json.py <input.csv> [regions.json] [output.html]")
        print("\nIf output.html is provided, data will be embedded into HTML file")
        print("Otherwise, JavaScript code will be saved to <csv_name>_data.js")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    regions_json = sys.argv[2] if len(sys.argv) > 2 else None
    output_html = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not Path(input_csv).exists():
        print(f"Error: Input file '{input_csv}' not found")
        sys.exit(1)
    
    if regions_json and not Path(regions_json).exists():
        print(f"Warning: Regions file '{regions_json}' not found")
        print("Continuing without region metadata...")
        regions_json = None
    
    print(f"Converting {input_csv}...")
    convert_csv_to_embedded_json(input_csv, regions_json, output_html)


if __name__ == "__main__":
    main()
