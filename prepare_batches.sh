#!/bin/bash

log_out="`date +%Y%m%d%H%M%S`".log;
err_out="`date +%Y%m%d%H%M%S`".err;

echo $log_out
echo $err_out

for x in `seq 9 9`;
do
    echo $x >> $log_out 2>> $err_out
    export EVENT_BATCH_ID=$x
    export BATCH_NUM=batch${EVENT_BATCH_ID}

    let "SED_START_IDX = (${EVENT_BATCH_ID} - 1) * 5 + 1"
    let "SED_END_IDX = ${EVENT_BATCH_ID} * 5"
    mkdir -p data/${BATCH_NUM}
    sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Disasters_and_accidents.ids.txt > data/${BATCH_NUM}/doc_clusters.txt
    sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Politics_and_conflicts.ids.txt >> data/${BATCH_NUM}/doc_clusters.txt

    python prepare_doc_batch.py \
        --wikinews cdec_wikinews/wikinews-0121-similar.json \
        --coling2018 cdec_wikinews/coling2018_out \
        --doc-clusters data/${BATCH_NUM}/doc_clusters.txt \
        --out cdec_wikinews/${BATCH_NUM} \
        >> $log_out 2>> $err_out
    
    python detection_pipeline.py \
        --dir cdec_wikinews/${BATCH_NUM} \
        --coling2018 cdec_wikinews/${BATCH_NUM}/coling2018_out \
        >> $log_out 2>> $err_out

    # ! run these on packs after expert event correction
    # # removing multipacks before regenerating
    # rm -r cdec_wikinews/${BATCH_NUM}/multipacks
    # python pair_pipeline.py \
    #     --dir cdec_wikinews/${BATCH_NUM} \
    #     --doc-pairs data/${BATCH_NUM}/doc_clusters.txt \
    #     --clique-threshold 4 \
    #     >> $log_out 2>> $err_out

done