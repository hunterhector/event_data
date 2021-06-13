#!/bin/bash

for i in `seq 0 4`;
do
    echo "----------------------"
    echo "cross-validation: k="$i
    python lemma_baseline.py \
        -docs raw_data/dataset_docs/ \
        -subtopics data_122/dev_${i}_subtopics.txt \
        -dev_path data_122/dev_${i}.json \
        -sim_threshold 0
    echo "----------------------"
done

python lemma_baseline.py \
    -docs raw_data/dataset_docs/ \
    -subtopics raw_data/dataset_splits/test_subtopics.txt \
    -dev_path data_122/test_pairs.json \
    -sim_threshold 0