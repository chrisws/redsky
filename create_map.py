import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# pip install cartopy

# Bounding box
LAT_MIN, LAT_MAX = -39, -34
LON_MIN, LON_MAX = 136, 142

def plot_bounding_box():
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([LON_MIN - 1, LON_MAX + 1, LAT_MIN - 1, LAT_MAX + 1], crs=ccrs.PlateCarree())

    # Add land, ocean, and borders
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.COASTLINE)

    # Draw bounding box
    lons = [LON_MIN, LON_MAX, LON_MAX, LON_MIN, LON_MIN]
    lats = [LAT_MIN, LAT_MIN, LAT_MAX, LAT_MAX, LAT_MIN]
    ax.plot(lons, lats, color='red', linewidth=2, transform=ccrs.PlateCarree(), label="Bounding Box")

    ax.set_title("Bounding Box for Regional SST/CHL Analysis")
    ax.legend(loc='lower left')

    plt.show()

if __name__ == "__main__":
    plot_bounding_box()
