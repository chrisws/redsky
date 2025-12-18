#
# Estimate expected VIIRS pixel count and classify data quality based on coverage.
#

import math
import sys

from viirs_regions import get_regions

def viirs_pixel_coverage(bbox, resolution_km=4):
    """
    Estimate expected VIIRS pixel count and classify data quality based on coverage.

    Parameters
    ----------
    lat_min, lat_max : float
        Latitude bounds in degrees.
    lon_min, lon_max : float
        Longitude bounds in degrees.
    resolution_km : float, optional
        VIIRS pixel spatial resolution (default: 4 km).

    Returns
    -------
    dict containing:
        - lat_km, lon_km : box size in km
        - area_km2 : area of box in km²
    """

    lon1, lon2, lat1, lat2 = bbox

    # Ensure proper min/max ordering (handles Southern Hemisphere)
    lon_min = min(lon1, lon2)
    lon_max = max(lon1, lon2)
    lat_min = min(lat1, lat2)  # Most negative (southernmost)
    lat_max = max(lat1, lat2)  # Least negative (northernmost)

    # Mean latitude for longitude scaling
    mean_lat = (lat_min + lat_max) / 2.0

    # Approximate conversion (1° lat ≈ 111.32 km)
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(mean_lat))

    # Compute bbox dimensions in km

    lat_km = (lat_max - lat_min) * km_per_deg_lat
    lon_km = (lon_max - lon_min) * km_per_deg_lon

    # Bounding box area
    area_km2 = lat_km * lon_km

    # Expected number of VIIRS pixels (area / pixel area)
    pixel_area = resolution_km ** 2
    expected_pixels = area_km2 / pixel_area

    return {
        "lat_km": lat_km,
        "lon_km": lon_km,
        "area_km2": area_km2,
        "expected_pixels": expected_pixels,
    }

print("\n## VIIRS Pixel Coverage Summary\n")
if len(sys.argv) == 2:
    regions, _ = get_regions(sys.argv[1])
    for region_name, bbox in regions.items():
        result = viirs_pixel_coverage(bbox)
        print (f"{region_name} {result}")
