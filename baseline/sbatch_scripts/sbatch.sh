#!/bin/bash

#SBATCH --time=0
#SBATCH --mem=10000
#SBATCH --output=slurm-out/slurm-%j.out
#SBATCH --gres=gpu:1

# cd ..
# python train.py train \
#     -train_path data_122/train.json \
#     -save_dir saved_models/ \
#     -epochs 5 \
#     -config configs/config_event_tag.json

cd ..
for i in `seq 1 5`;
do
    python train.py train \
        -train_path data_155/train.json \
        -save_dir saved_models/ \
        -epochs 5 \
        -config configs/config_event_tag.json
done