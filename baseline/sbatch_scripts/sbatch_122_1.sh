#!/bin/bash

#SBATCH --time=0
#SBATCH --mem=10000
#SBATCH --output=slurm-out/slurm-%j.out
#SBATCH --gres=gpu:1

cd ..
python train.py train \
    -train_path data_122/train_1.json \
    -dev_path data_122/dev_1.json \
    -save_dir saved_models/ \
    -config configs/config_event_tag.json