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
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'GAB' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Ceduna' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Port Lincoln' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Spencer Gulf N' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Spencer Gulf S' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - NW' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - NE' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - SW' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'SVG - SE' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'KI - W' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'KI - E' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Victor Harbor' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Victor Harbour-Mt Gambier' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Mt Gambier' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_plot.py ${STUDY}/sst.csv ${STUDY}/chlr-a.csv 20180105 'Port Fairy' ${STUDY}/images) && \
    (cd ${VIIRS} && python viirs_map.py "Region map" ${STUDY}/regions.json ${STUDY}/images/map.png) && \
    (cd ${VIIRS} && python viirs_energy_analysis.py --regions ../study/sa/regions.json ../study/sa/sst.csv --plot ../study/sa/images/energy.png --output ../study/sa/energy.csv) && \
    (cd ${VIIRS} && python viirs_hab_analysis.py --regions ../study/sa/regions.json ../study/sa/chlr-a.csv --plot ../study/sa/images/hab.png --report ../study/sa/hab.md) && \
    echo '## South Australian algal bloom investigation with VIIRS SST and Chlr-A data' > ${MARKDOWN} && \
    echo '![Regions](./study/sa/images/map.png)' >> ${MARKDOWN} && \
    echo '![GAB](./study/sa/images/viirs_timeseries_GAB.png)' >> ${MARKDOWN} && \
    echo '![Ceduna](./study/sa/images/viirs_timeseries_Ceduna.png)' >> ${MARKDOWN} && \
    echo '![Port Lincoln](./study/sa/images/viirs_timeseries_PortLincoln.png)' >> ${MARKDOWN} && \
    echo '![Spencer Gulf N](./study/sa/images/viirs_timeseries_SpencerGulfN.png)' >> ${MARKDOWN} && \
    echo '![Spencer Gulf E](./study/sa/images/viirs_timeseries_SpencerGulfS.png)' >> ${MARKDOWN} && \
    echo '![SVG - NW](./study/sa/images/viirs_timeseries_SVGNW.png)' >> ${MARKDOWN} && \
    echo '![SVG - NE](./study/sa/images/viirs_timeseries_SVGNE.png)' >> ${MARKDOWN} && \
    echo '![SVG - SW](./study/sa/images/viirs_timeseries_SVGSW.png)' >> ${MARKDOWN} && \
    echo '![SVG - SE](./study/sa/images/viirs_timeseries_SVGSE.png)' >> ${MARKDOWN} && \
    echo '![KI - W](./study/sa/images/viirs_timeseries_KIW.png)' >> ${MARKDOWN} && \
    echo '![KI - E](./study/sa/images/viirs_timeseries_KIE.png)' >> ${MARKDOWN} && \
    echo '![Victor Harbor](./study/sa/images/viirs_timeseries_VictorHarbor.png)' >> ${MARKDOWN} && \
    echo '![Victor Harbour-Mt Gambier](./study/sa/images/viirs_timeseries_VictorHarbourMtGambier.png)' >> ${MARKDOWN} && \
    echo '![Mt Gambier](./study/sa/images/viirs_timeseries_MtGambier.png)' >> ${MARKDOWN} && \
    echo '![Port Fairy](./study/sa/images/viirs_timeseries_PortFairy.png)' >> ${MARKDOWN} && \
    echo '### Yearly mean values' >> ${MARKDOWN} && \
    echo '```' >> ${MARKDOWN}&& \
    (cd ${VIIRS} && python viirs_yearly_mean.py ${STUDY}/chlr-a.csv >> ${MARKDOWN_1}) && \
    echo '```' >> ${MARKDOWN} && \
    (cd ${VIIRS} && python viirs_coverage.py ${STUDY}/regions.json >> ${MARKDOWN_1}) && \
    echo Last updated: `date` >> ${MARKDOWN}
