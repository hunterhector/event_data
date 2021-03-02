#!/bin/bash

if [ ! $# -eq 1 ]; then
    echo "Usage: bash prepare_batches.sh <MODE>"
    echo "MODE can be single or multi"
    exit 1
fi

log_out="logs/`date +%Y%m%d%H%M%S`".log;
err_out="logs/`date +%Y%m%d%H%M%S`".err;

echo $log_out
echo $err_out

# single (upto human correction) or multi (post human correction)
MODE=$1

for x in `seq 1 1`;
do
    echo $x >> $log_out 2>> $err_out
    export EVENT_BATCH_ID=$x
    export BATCH_NUM=batch${EVENT_BATCH_ID}

    if [ "$MODE" == "single" ]; then
        let "SED_START_IDX = (${EVENT_BATCH_ID} - 1) * 5 + 1"
        let "SED_END_IDX = ${EVENT_BATCH_ID} * 5"
        mkdir -p data/${BATCH_NUM}
        sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Disasters_and_accidents.ids.txt > data/${BATCH_NUM}/doc_clusters.txt
        sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Politics_and_conflicts.ids.txt >> data/${BATCH_NUM}/doc_clusters.txt

        python prepare_doc_batch.py \
            --wikinews cdec_wikinews/wikinews-022421-similar.json \
            --coling2018 cdec_wikinews/coling2018_out \
            --doc-clusters data/${BATCH_NUM}/doc_clusters.txt \
            --out cdec_wikinews/${BATCH_NUM} \
            >> $log_out 2>> $err_out
        
        python detection_pipeline.py \
            --dir cdec_wikinews/${BATCH_NUM} \
            --coling2018 cdec_wikinews/${BATCH_NUM}/coling2018_out \
            >> $log_out 2>> $err_out
    
    elif [ "$MODE" == "multi" ]; then
        # ! NOTE: this is to be done after event mention correction

        STAVE_DB_PATH=cdec_wikinews/post_correction/db.sqlite3
        BATCH_OUT_PATH=cdec_wikinews/post_correction/${BATCH_NUM}
        echo "loading stave_db from "${STAVE_DB_PATH} >> $log_out 2>> $err_out

        # regenerate data packs after event mention correction 
        echo "writing new packs to "${BATCH_OUT_PATH} >> $log_out 2>> $err_out
        python load_stave_single-doc.py \
            --sql ${STAVE_DB_PATH} \
            --project-name cdec_${BATCH_NUM} \
            --doc-clusters data/${BATCH_NUM}/doc_clusters.txt \
            --out ${BATCH_OUT_PATH}/packs \
            >> $log_out 2>> $err_out

        # removing multipacks before regenerating
        rm -rf ${BATCH_OUT_PATH}/multipacks
        python pair_pipeline.py \
            --dir ${BATCH_OUT_PATH} \
            --doc-pairs data/${BATCH_NUM}/doc_clusters.txt \
            --clique-threshold 4 \
            >> $log_out 2>> $err_out
    else
        echo "unknown mode, only options are single/multi"
    fi

done