#!/bin/bash

python preprocess.py \
    -coref_pairs raw_data/dataset_positive_labels/all_positive_labels.json \
    -docs raw_data/dataset_docs/ \
    -splits raw_data/dataset_splits/ \
    -out_dir data_155/