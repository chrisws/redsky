#
# Region configuration with detailed St Vincent Gulf subsectors
# Format: [lon_min, lon_max, lat_min, lat_max]
# Expected subsector sizes (for reference)
# Each northern subsector: ~45 km (E-W) × ~40-45 km (N-S) = ~1,800-2,000 km²
# At 4km resolution: ~110-125 pixels per subsector
# This is plenty for robust statistics

import json

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

if __name__ == '__main__':
    # test
    regions, colors = get_regions("study/sa/regions.json")
    print("Region Bounding Boxes:")
    print("=" * 60)
    for region_name, bbox in regions.items():
        min_lon, max_lon, min_lat, max_lat = bbox
        print(f"{region_name:30s}: [{min_lon:6.1f}, {max_lon:6.1f}, {min_lat:6.1f}, {max_lat:6.1f}]")
    for region_name, code in colors.items():
        print(f"{region_name:30s}: [{code}]")


