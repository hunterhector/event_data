#!/bin/bash

#SBATCH --time=0
#SBATCH --mem=10000
#SBATCH --output=slurm-out/slurm-%j.out
#SBATCH --gres=gpu:1

cd ..

python train.py inference \
    -model_path saved_models/coref_classifier_2021-06-11_22-18-27.bin \
    -data_path data_122/dev_1.json \
    -preds output_preds/preds.json