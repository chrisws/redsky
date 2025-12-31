#!/usr/bin/env python3
"""
Define and visualize South Australia coastal regions for HAB monitoring.
"""

import argparse
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.patches import Rectangle
from viirs_regions import get_regions

def plot_regions(title, output_png, regions, colors):
    """Plot the regions on a map using Cartopy."""
    fig = plt.figure(figsize=(14, 10))

    # Set up the map projection
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    min_lon = 999
    max_lon  = -999
    min_lat = 999
    max_lat = -999
    for region_name, bbox in regions.items():
        lon1, lon2, lat1, lat2 = bbox
        min_lon = min(min_lon, min(lon1, lon2))
        max_lon = max(max_lon, max(lon1, lon2))
        min_lat = min(min_lat, min(lat1, lat2))
        max_lat = max(max_lat, max(lat1, lat2))

    # Set extent to cover bounding region
    offset = 1.5
    ax.set_extent([min_lon - offset, max_lon + offset, min_lat - offset, max_lat + offset], crs=ccrs.PlateCarree())

    # Use higher resolution coastlines
    ax.coastlines(resolution='10m')  # Options: '110m', '50m', '10m'
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'))
    ax.add_feature(cfeature.LAKES.with_scale('10m'), edgecolor='blue', facecolor='lightblue')

    # Add map features
    ax.add_feature(cfeature.LAND, facecolor='lightgray', edgecolor='black', linewidth=0.5)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.add_feature(cfeature.COASTLINE, linewidth=1)
    ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)

    # Add gridlines
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                      alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False

    # Plot each region as a bounding box
    for region_name, bbox in regions.items():
        lon1, lon2, lat1, lat2 = bbox

        # Ensure proper min/max ordering (handles Southern Hemisphere)
        min_lon = min(lon1, lon2)
        max_lon = max(lon1, lon2)
        min_lat = min(lat1, lat2)  # Most negative (southernmost)
        max_lat = max(lat1, lat2)  # Least negative (northernmost)

        width = max_lon - min_lon
        height = max_lat - min_lat
        color = colors[region_name]

        # Draw rectangle
        rect = Rectangle((min_lon, min_lat), width, height,
                        linewidth=2, edgecolor=color, facecolor='none',
                        transform=ccrs.PlateCarree(), label=region_name,
                        linestyle='-', alpha=0.8)
        ax.add_patch(rect)

        # Add label in center of box
        center_lon = min_lon + width / 2
        center_lat = min_lat + height / 2
        fontSize = 7
        if region_name.startswith("SVG"):
            fontSize = 5.5
        ax.text(center_lon, center_lat, region_name.replace('-', '-\n'),
               transform=ccrs.PlateCarree(),
               fontsize=fontSize,
               ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                        edgecolor=color, alpha=0.8))

    plt.title(title, fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches='tight')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'title',
        type=str,
        help='Map title'
    )
    parser.add_argument(
        'regions_json',
        type=str,
        help='The regions to inspect'
    )
    parser.add_argument(
        'output_png',
        type=str,
        help='The map output'
    )
    args = parser.parse_args()

    regions, colors = get_regions(args.regions_json)
    plot_regions(args.title, args.output_png, regions, colors)
