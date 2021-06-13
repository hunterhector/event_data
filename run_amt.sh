#!/bin/bash

python prepare_mturk_data.py \
    amt_data/db.sqlite3 \
    amt_data/mturk_tinydb.json \
    cdec_wikinews/latest/packs/ \
    data/topics/Disasters_and_accidents.ids.txt \
    -nrounds 1 \
    -ngroups 1

cd processors/

python crowdsource_annotator.py \
    ../amt_data/db.sqlite3 \
    ../amt_data/mturk_tinydb.json \
    ../amt_configs/mturk_config.json \
    --dryrun