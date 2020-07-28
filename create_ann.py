import os
import sys

input_dir = '../brat_data/input/'

for file in os.listdir(input_dir):
    if file.endswith('.txt'):
        ann_file = file.replace('.txt', '.ann')
        if not os.path.exists(input_dir+ann_file):
            with open(input_dir+ann_file, 'w') as f:
                f.write('')