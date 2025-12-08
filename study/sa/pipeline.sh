#!/bin/bash

# overview of study regions
# python viirs_map.py "South Australia Coastal Regions for HAB Monitoring" ../study/sa/regions.json ../study/sa/images/map.png

VIIRS=../../viirs

echo "Updating" && \
    ${VIIRS}/viirs_downloader.sh -t ${VIIRS}/data/viirs_sst && \
    ${VIIRS}/viirs_downloader.sh ${VIIRS}/data/viirs_chlr-a && \
    (cd ${VIIRS} && python viirs_region_extractor.py ../study/sa/regions.json ./data/viirs_sst ../study/sa/sst.csv) && \
    (cd ${VIIRS} && python viirs_region_extractor.py ../study/sa/regions.json ./data/viirs_chlr-a ../study/sa/chlr-a.csv) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'Ceduna-Port Lincoln' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'Spencer Gulf N' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'Spencer Gulf S' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'SVG - NW' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'SVG - NE' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'SVG - SW' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'SVG - SE' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'Victor Harbor' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'Victor Harbour-Mt Gambier' ../study/sa/images) && \
    (cd ${VIIRS} && python viirs_plot.py ../study/sa/sst.csv ../study/sa/chlr-a.csv 20180105 'Mt Gambier-Port Fairy' ../study/sa/images)

