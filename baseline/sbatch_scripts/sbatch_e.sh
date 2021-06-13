#!/bin/bash

#SBATCH --time=0
#SBATCH --mem=10000
#SBATCH --output=slurm-out/slurm-%j.out
#SBATCH --gres=gpu:1

cd ..
# python train.py inference \
#     -model_path saved_models/coref_classifier_2021-06-12_00-19-20.bin \
#     -data_path data_122/test_pairs.json
python train.py inference \
    -model_path saved_models/coref_classifier_2021-06-12_01-26-43.bin \
    -data_path data_122/test_pairs.json
python train.py inference \
    -model_path saved_models/coref_classifier_2021-06-12_01-27-15.bin \
    -data_path data_122/test_pairs.json
python train.py inference \
    -model_path saved_models/coref_classifier_2021-06-12_01-28-45.bin \
    -data_path data_122/test_pairs.json
python train.py inference \
    -model_path saved_models/coref_classifier_2021-06-12_01-29-32.bin \
    -data_path data_122/test_pairs.json