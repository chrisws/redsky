#!/bin/bash

VIIRS=../../viirs
STUDY=../study/gab
STUDY_1=./study/gab
MARKDOWN=../../GAB.md
MARKDOWN_1=../GAB.md

echo "Updating" && \
    ${VIIRS}/viirs_downloader.sh -t ${VIIRS}/data/viirs_sst && \
    ${VIIRS}/viirs_downloader.sh ${VIIRS}/data/viirs_chlr-a && \
    (cd ${VIIRS} && python viirs_region_extractor.py ${STUDY}/regions.json ./data/viirs_sst ${STUDY}/sst.csv --start-date 20180104) && \
    (cd ${VIIRS} && python viirs_region_extractor.py ${STUDY}/regions.json ./data/viirs_chlr-a ${STUDY}/chlr-a.csv --start-date 20180104) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Esperance_1' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Esperance_2' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Esperance_3' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Mundrabilla' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Eucla_1' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Eucla_2' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Yalata' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Ceduna' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_map.py "Region map" ${STUDY}/regions.json ${STUDY}/images/map.png) && \
    echo '## South Australian algal bloom investigation' > ${MARKDOWN} && \
    echo "![Regions](${STUDY_1}/images/map.png)" >> ${MARKDOWN} && \
    echo "![Esperance_1](${STUDY_1}/images/viirs_timeseries_Esperance_1.png)" >> ${MARKDOWN} && \
    echo "![Esperance_2](${STUDY_1}/images/viirs_timeseries_Esperance_2.png)" >> ${MARKDOWN} && \
    echo "![Esperance_3](${STUDY_1}/images/viirs_timeseries_Esperance_3.png)" >> ${MARKDOWN} && \
    echo "![Mundrabilla](${STUDY_1}/images/viirs_timeseries_Mundrabilla.png)" >> ${MARKDOWN} && \
    echo "![Eucla_1](${STUDY_1}/images/viirs_timeseries_Eucla_1.png)" >> ${MARKDOWN} && \
    echo "![Eucla_2](${STUDY_1}/images/viirs_timeseries_Eucla_2.png)" >> ${MARKDOWN} && \
    echo "![Yalata](${STUDY_1}/images/viirs_timeseries_Yalata.png)" >> ${MARKDOWN} && \
    echo "![Ceduna](${STUDY_1}/images/viirs_timeseries_Ceduna.png)" >> ${MARKDOWN} && \
    echo '### Yearly mean values' >> ${MARKDOWN} && \
    echo '```' >> ${MARKDOWN}&& \
    (cd ${VIIRS} && python viirs_yearly_mean.py ${STUDY}/chlr-a.csv >> ${MARKDOWN_1}) && \
    echo '```' >> ${MARKDOWN} && \
    (cd ${VIIRS} && python viirs_coverage.py ${STUDY}/regions.json >> ${MARKDOWN_1}) && \
    echo >> ${MARKDOWN} && \
    echo '---' >> ${MARKDOWN} && \
    (cd ${VIIRS} && python viirs_energy_analysis.py --regions ${STUDY}/regions.json ${STUDY}/sst.csv --plot ${STUDY}/images/energy.png --output ${STUDY}/energy.csv) >> ${MARKDOWN} && \
    echo Last updated: `date` >> ${MARKDOWN} && \
    optipng images/*.png
