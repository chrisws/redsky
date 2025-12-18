#!/bin/bash

VIIRS=../../viirs
STUDY=../study/sa
MARKDOWN=../../README.md
MARKDOWN_1=../README.md

echo "Updating" && \
    ${VIIRS}/viirs_downloader.sh -t ${VIIRS}/data/viirs_sst && \
    ${VIIRS}/viirs_downloader.sh ${VIIRS}/data/viirs_chlr-a && \
    (cd ${VIIRS} && python viirs_region_extractor.py ${STUDY}/regions.json ./data/viirs_sst ${STUDY}/sst.csv) && \
    (cd ${VIIRS} && python viirs_region_extractor.py ${STUDY}/regions.json ./data/viirs_chlr-a ${STUDY}/chlr-a.csv) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Ceduna-Port Lincoln' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Spencer Gulf N' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Spencer Gulf S' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - NW' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - NE' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - SW' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - SE' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Victor Harbor' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Victor Harbour-Mt Gambier' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Mt Gambier-Port Fairy' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_map.py "Region map" ${STUDY}/regions.json ${STUDY}/images/map.png) && \
    echo '## South Australian algal bloom investigation with VIIRS SST and Chlr-A data' > ${MARKDOWN} && \
    echo '![Regions](./study/sa/images/map.png)' >> ${MARKDOWN} && \
    echo '![Ceduna-Port Lincoln](./study/sa/images/viirs_timeseries_CedunaPortLincoln.png)' >> ${MARKDOWN} && \
    echo '![Mt Gambier-Port Fairy](./study/sa/images/viirs_timeseries_MtGambierPortFairy.png)' >> ${MARKDOWN} && \
    echo '![Spencer Gulf N](./study/sa/images/viirs_timeseries_SpencerGulfN.png)' >> ${MARKDOWN} && \
    echo '![Spencer Gulf E](./study/sa/images/viirs_timeseries_SpencerGulfS.png)' >> ${MARKDOWN} && \
    echo '![SVG - NE](./study/sa/images/viirs_timeseries_SVGNE.png)' >> ${MARKDOWN} && \
    echo '![SVG - NE](./study/sa/images/viirs_timeseries_SVGNW.png)' >> ${MARKDOWN} && \
    echo '![SVG - SE](./study/sa/images/viirs_timeseries_SVGSE.png)' >> ${MARKDOWN} && \
    echo '![SVG - SW](./study/sa/images/viirs_timeseries_SVGSW.png)' >> ${MARKDOWN} && \
    echo '![Victor Harbor](./study/sa/images/viirs_timeseries_VictorHarbor.png)' >> ${MARKDOWN} && \
    echo '![Victor Harbour-Mt Gambier](./study/sa/images/viirs_timeseries_VictorHarbourMtGambier.png)' >> ${MARKDOWN} && \
    echo '### Yearly mean values' >> ${MARKDOWN} && \
    echo '```' >> ${MARKDOWN}&& \
    (cd ${VIIRS} && python viirs_yearly_mean.py ${STUDY}/chlr-a.csv >> ${MARKDOWN_1}) && \
    (cd ${VIIRS} && python viirs_coverage.py ${STUDY}/regions.json >> ${MARKDOWN_1}) && \
    echo '```' >> ${MARKDOWN} && \
    echo Last updated: `date` >> ${MARKDOWN}
