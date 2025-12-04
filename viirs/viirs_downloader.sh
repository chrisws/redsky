#!/bin/bash
#
# Download daily chlorophyll-a or SST satellite data from NASA OceanData.
#

set -euo pipefail

# Configuration
BASE_URL="https://oceandata.sci.gsfc.nasa.gov/cgi/getfile"
COOKIE_FILE=$(mktemp)

# Cleanup on exit
trap 'rm -f "$COOKIE_FILE"' EXIT

usage() {
    echo "Usage: $0 <output_folder>"
    echo
    echo "Download daily chlorophyll-a or SST satellite data from NASA OceanData"
    echo
    echo "Arguments:"
    echo "  [-s 20120102]    Optional start date to fetch"
    echo "  [-e 20171212]    Optional end date to fetch"
    echo "  [-p]             Optional fetch SNPP data in lieu of JPSS1"
    echo "  [-t]             Optional fetch SST in lieu of CHLR-A"
    echo "  output_folder    Directory to save downloaded files"
    echo
    echo "Requirements:"
    echo "  - ~/.netrc file with credentials for urs.earthdata.nasa.gov"
    exit 1
}

START_DATE="20171213"
END_DATE=$(date +%Y%m%d)
PREFIX="JPSS1"
FORMAT="CHL.chlor_a"

# JPSS1_VIIRS.20171213.L3m.DAY.CHL.chlor_a.4km.nc
#  SNPP_VIIRS.20120102.L3m.DAY.CHL.chlor_a.4km.nc
# JPSS1_VIIRS.20180104.L3m.DAY.NSST.sst.4km.nc

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s)
      if [[ -n "$2" && "$2" != -* ]]; then
        START_DATE="$2"
        shift 2
      fi
      ;;
    -e)
      if [[ -n "$2" && "$2" != -* ]]; then
        END_DATE="$2"
        shift 2
      fi
      ;;
    -p)
      PREFIX="SNPP"
      shift
      ;;
    -t)
      FORMAT="NSST.sst"
      shift
      ;;
    --)  # stop option parsing
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
    *)  # first non-option argument encountered
      break
      ;;
  esac
done

# Capture the final positional argument (required)
OUTPUT_DIR="$1"

if [[ -z "$OUTPUT_DIR" ]]; then
    usage
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check for .netrc
if [ ! -f ~/.netrc ]; then
    echo "Error: ~/.netrc file not found" >&2
    echo "Please create ~/.netrc with credentials for urs.earthdata.nasa.gov" >&2
    exit 1
fi

# Convert date string to epoch seconds (for date arithmetic)
date_to_epoch() {
    date -d "$1" +%s 2>/dev/null || date -j -f "%Y%m%d" "$1" +%s 2>/dev/null
}

# Convert epoch seconds to YYYYMMDD format
epoch_to_date() {
    date -d "@$1" +%Y%m%d 2>/dev/null || date -r "$1" +%Y%m%d 2>/dev/null
}

# Parse date from filename
parse_date_from_filename() {
    local filename="$1"
    if [[ "$filename" =~ \.([0-9]{8})\. ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
}

# Find the latest date in output folder
get_latest_date() {
    local latest_date=""
    local latest_epoch=0

    for file in "$OUTPUT_DIR"/"${PREFIX}"_VIIRS.*.nc; do
        [ -e "$file" ] || continue
        local file_date=$(parse_date_from_filename "$(basename "$file")")
        if [ -n "$file_date" ]; then
            local file_epoch=$(date_to_epoch "$file_date")
            if [ "$file_epoch" -gt "$latest_epoch" ]; then
                latest_epoch=$file_epoch
                latest_date=$file_date
            fi
        fi
    done

    if [ -z "$latest_date" ]; then
        # No files found, return day before start date
        local start_epoch=$(date_to_epoch "$START_DATE")
        local prev_epoch=$((start_epoch - 86400))
        epoch_to_date "$prev_epoch"
    else
        echo "$latest_date"
    fi
}

# Generate filename for a given date
generate_filename() {
    local date_str="$1"
    echo "${PREFIX}_VIIRS.${date_str}.L3m.DAY.${FORMAT}.4km.nc"
}

# Generate a 'near realtime data' filename (lower quality, but more likely to be available)
generate_nrt_filename() {
    local date_str="$1"
    echo "${PREFIX}_VIIRS.${date_str}.L3m.DAY.${FORMAT}.4km.NRT.nc"
}

# Download a single file
download_file() {
    local url="$1"
    local output_path="$2"
    local filename=$(basename "$output_path")

    echo -n "Downloading: $filename ... "

    if curl -n -c "$COOKIE_FILE" -b "$COOKIE_FILE" -L -f -s -S \
        -o "$output_path" "$url" 2>/dev/null; then
        echo "✓"
        return 0
    else
        local status=$?
        # Remove partial download
        [ -f "$output_path" ] && rm -f "$output_path"

        # Check if it was a 404 (file not available)
        if [ $status -eq 22 ]; then
            echo "Not available"
            exit 0
        else
            echo "Failed"
        fi
        return 1
    fi
}

# Main execution
main() {
    echo "Output folder: $OUTPUT_DIR"

    # Get latest date in folder
    latest_date=$(get_latest_date)
    echo "Latest date found: ${latest_date:0:4}-${latest_date:4:2}-${latest_date:6:2}"

    # Calculate next date to download
    latest_epoch=$(date_to_epoch "$latest_date")
    next_epoch=$((latest_epoch + 86400))
    next_date=$(epoch_to_date "$next_epoch")

    # Current date
    current_date=${END_DATE}
    current_epoch=$(date_to_epoch "$current_date")

    echo "Starting download from: ${next_date:0:4}-${next_date:4:2}-${next_date:6:2}"
    echo "Current/end date: ${current_date:0:4}-${current_date:4:2}-${current_date:6:2}"
    echo

    # Calculate total days
    total_days=$(( (current_epoch - next_epoch) / 86400 + 1 ))
    downloaded=0
    skipped=0
    not_available=0
    nrt=0

    # Download loop
    download_epoch=$next_epoch
    count=0

    while [ "$download_epoch" -le "$current_epoch" ]; do
        download_date=$(epoch_to_date "$download_epoch")
        if (( nrt )); then
            filename=$(generate_nrt_filename "$download_date")
        else
            filename=$(generate_filename "$download_date")
        fi
        output_path="$OUTPUT_DIR/$filename"
        url="$BASE_URL/$filename"

        if [ -f "$output_path" ]; then
            echo "Skipping: $filename (already exists)"
            skipped=$((skipped + 1))
        else
            if download_file "$url" "$output_path"; then
                downloaded=$((downloaded + 1))
            else
                # if (( ! nrt )); then
                #     nrt=1
                #     continue;
                # fi
                not_available=$((not_available + 1))
            fi
        fi

        count=$((count + 1))
        echo -n "[$count/$total_days] "
        download_epoch=$((download_epoch + 86400))
    done

    echo
    echo "Complete! Downloaded: $downloaded, Skipped: $skipped, Not available: $not_available"
}

main
