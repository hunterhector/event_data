#!/bin/bash

if [ ! $# -eq 1 ]; then
    echo "Usage: bash prepare_batches.sh <MODE>"
    echo "MODE can be single or multi"
    exit 1
fi

# single (upto human correction) or multi (post human correction)
MODE=$1

ROOT=$PWD
AUTO_PACKS=$ROOT/cdec_wikinews/latest/packs
DOC_GROUPS=$ROOT/data/topics/Disasters_and_accidents.ids.txt

if [ "$MODE" == "single" ]; then
    python prepare_doc_batch.py \
        -packs $AUTO_PACKS \
        -doc_clusters $DOC_GROUPS \
        -pack_db $ROOT/amt_data/pack_tinydb.json \
        -count 20 \
        -out $ROOT/cdec_wikinews/latest/sorted_doc_clusters.txt

elif [ "$MODE" == "multi" ]; then
    SINGLEDOC_DB=$ROOT/cdec_wikinews/post_correction/db.sqlite3
    PACK_DB=$ROOT/amt_data/pack_tinydb.json
    PACK_OUT=$ROOT/cdec_wikinews/latest/corrected
    N_GROUPS=10
    
    cd event_correction
    # update the pack db (local copy)
    python update_pack_db.py \
        $SINGLEDOC_DB \
        $PACK_DB
    
    # add --overwrite option if we want to overwrite packs
    python write_corrected_packs.py \
        $SINGLEDOC_DB \
        $AUTO_PACKS \
        $PACK_DB \
        $PACK_OUT/packs \
        $DOC_GROUPS \
        $N_GROUPS

    cd ..

    # write multipacks
    # add --overwrite option to overwrite existing multipacks
    python pair_pipeline.py \
        --dir $PACK_OUT \
        --doc-pairs $DOC_GROUPS \
        --clique-threshold 4

else
    echo "unknown mode, only options are single/multi"
fi
