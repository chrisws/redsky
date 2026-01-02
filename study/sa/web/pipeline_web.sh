#!/bin/bash

VIIRS=../../../viirs
STUDY=../study/sa

echo "Updating" && \
    ${VIIRS}/viirs_nrt_downloader.sh 20230101 ${VIIRS}/data/viirs_nrt-chlr-a && \
    (cd ${VIIRS} && python viirs_region_extractor.py ${STUDY}/regions.json ./data/viirs_nrt-chlr-a ${STUDY}/web/chlr-a-nrt.csv) && \
    python csv_to_json_converter.py chlr-a-nrt.csv ../regions.json && \
    cp chlorophyll_data.js ../../../../chrisws.github.io/ &&\
    cp bloom-watch.html ../../../../chrisws.github.io/
