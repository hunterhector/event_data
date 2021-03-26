#!/bin/bash

if [ ! $# -eq 1 ]; then
    echo "Usage: bash prepare_batches.sh <MODE>"
    echo "MODE can be single or multi"
    exit 1
fi

# single (upto human correction) or multi (post human correction)
MODE=$1

if [ "$MODE" == "single" ]; then
    python prepare_doc_batch.py \
        -packs cdec_wikinews/latest/packs \
        -doc_clusters data/topics/Disasters_and_accidents.ids.txt \
        -pack_db amt_data/pack_tinydb.json \
        -count 20 \
        -out cdec_wikinews/latest/sorted_doc_clusters.txt
fi
