#!/bin/bash

VIIRS=../../viirs
STUDY=../study/sa
STUDY_1=./study/sa
MARKDOWN=../../README.md
MARKDOWN_1=../README.md

echo "Updating" && \
    ${VIIRS}/viirs_downloader.sh -t ${VIIRS}/data/viirs_sst && \
    ${VIIRS}/viirs_downloader.sh ${VIIRS}/data/viirs_chlr-a && \
    (cd ${VIIRS} && python viirs_region_extractor.py ${STUDY}/regions.json ./data/viirs_sst ${STUDY}/sst.csv) && \
    (cd ${VIIRS} && python viirs_region_extractor.py ${STUDY}/regions.json ./data/viirs_chlr-a ${STUDY}/chlr-a.csv) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'GAB' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Ceduna E' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Ceduna W' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Pt Lincoln E' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Pt Lincoln W' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Spencer Gulf N' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Spencer Gulf C' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Spencer Gulf S' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - NW' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - NE' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - SW' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - SE' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'KI - W' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'KI - E' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Victor - E' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Victor - W' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Lk Alex' ${STUDY}/images --max_gap_days 250) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Victor Harbour-Mt Gambier' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Mt Gambier' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Pt Fairy' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_map.py "Region map" ${STUDY}/regions.json ${STUDY}/images/map.png) && \
    (cd ${VIIRS} && python viirs_hab_analysis.py --regions ${STUDY}/regions.json ${STUDY}/chlr-a.csv --plot ${STUDY}/images/hab.png --report ${STUDY}/hab.md) && \
    echo '## South Australian algal bloom investigation with VIIRS SST and Chlr-A data' > ${MARKDOWN} && \
    echo "![Regions](${STUDY_1}/images/map.png)" >> ${MARKDOWN} && \
    echo "![GAB](${STUDY_1}/images/viirs_timeseries_GAB.png)" >> ${MARKDOWN} && \
    echo "![Ceduna E](${STUDY_1}/images/viirs_timeseries_CedunaE.png)" >> ${MARKDOWN} && \
    echo "![Ceduna W](${STUDY_1}/images/viirs_timeseries_CedunaW.png)" >> ${MARKDOWN} && \
    echo "![Pt Lincoln E](${STUDY_1}/images/viirs_timeseries_PtLincolnE.png)" >> ${MARKDOWN} && \
    echo "![Pt Lincoln W](${STUDY_1}/images/viirs_timeseries_PtLincolnW.png)" >> ${MARKDOWN} && \
    echo "![Spencer Gulf N](${STUDY_1}/images/viirs_timeseries_SpencerGulfN.png)" >> ${MARKDOWN} && \
    echo "![Spencer Gulf C](${STUDY_1}/images/viirs_timeseries_SpencerGulfC.png)" >> ${MARKDOWN} && \
    echo "![Spencer Gulf E](${STUDY_1}/images/viirs_timeseries_SpencerGulfS.png)" >> ${MARKDOWN} && \
    echo "![SVG - NW](${STUDY_1}/images/viirs_timeseries_SVGNW.png)" >> ${MARKDOWN} && \
    echo "![SVG - NE](${STUDY_1}/images/viirs_timeseries_SVGNE.png)" >> ${MARKDOWN} && \
    echo "![SVG - SW](${STUDY_1}/images/viirs_timeseries_SVGSW.png)" >> ${MARKDOWN} && \
    echo "![SVG - SE](${STUDY_1}/images/viirs_timeseries_SVGSE.png)" >> ${MARKDOWN} && \
    echo "![KI - W](${STUDY_1}/images/viirs_timeseries_KIW.png)" >> ${MARKDOWN} && \
    echo "![KI - E](${STUDY_1}/images/viirs_timeseries_KIE.png)" >> ${MARKDOWN} && \
    echo "![Victor - W](${STUDY_1}/images/viirs_timeseries_VictorW.png)" >> ${MARKDOWN} && \
    echo "![Victor - E](${STUDY_1}/images/viirs_timeseries_VictorE.png)" >> ${MARKDOWN} && \
    echo "![Lk Alex](${STUDY_1}/images/viirs_timeseries_LkAlex.png)" >> ${MARKDOWN} && \
    echo "![Victor Harbour-Mt Gambier](${STUDY_1}/images/viirs_timeseries_VictorHarbourMtGambier.png)" >> ${MARKDOWN} && \
    echo "![Mt Gambier](${STUDY_1}/images/viirs_timeseries_MtGambier.png)" >> ${MARKDOWN} && \
    echo "![Pt Fairy](${STUDY_1}/images/viirs_timeseries_PtFairy.png)" >> ${MARKDOWN} && \
    (cd ${VIIRS} && python viirs_energy_analysis.py --regions ${STUDY}/regions.json ${STUDY}/sst.csv --plot ${STUDY}/images/energy.png --output ${STUDY}/energy.csv >> ${MARKDOWN_1}) && \
    echo '### Yearly mean values (chlr-a)' >> ${MARKDOWN} && \
    echo '```' >> ${MARKDOWN}&& \
    (cd ${VIIRS} && python viirs_yearly_mean.py ${STUDY}/chlr-a.csv >> ${MARKDOWN_1}) && \
    echo '```' >> ${MARKDOWN} && \
    (cd ${VIIRS} && python viirs_coverage.py ${STUDY}/regions.json >> ${MARKDOWN_1}) && \
    cat NOTES.md >> ${MARKDOWN} && \
    echo >> ${MARKDOWN} && \
    echo '---' >> ${MARKDOWN} && \
    echo Last updated: `date` >> ${MARKDOWN} && \
    optipng -clobber images/*.png
