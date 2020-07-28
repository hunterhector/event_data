import glob
import sys
import os
import json
import brat_tool
import spacy
import argparse

nlp = spacy.load('en_core_web_sm')

def replace_discontinuous_event_with_its_head(ann_file_path):
    with open(ann_file_path, 'r', encoding="utf-8") as f:
        ann_data = f.read()
        
    ann_data = brat_tool.BratAnnotations(ann_data)
    events = ann_data.getEventAnnotationList()
    new_event_list = list()
    
    for event in events:
        # code snippets from Matz: dependency head look-up methods
        if not event.textbound.separated:  # for continuous event
            new_event_list.append(event)
        else:
            """
            get root token of discontinuous event from Matz
            """
            root = str()
            root_idx = 0
            for idx, token in enumerate(nlp(event.text)): 
                if token.head == token:
                    root = token
                    root_idx = idx
            event.textbound.text = root.text
            event.textbound.start_pos = event.textbound.start_pos[root_idx]
            event.textbound.end_pos = event.textbound.end_pos[root_idx]
            new_event_list.append(event)
    return new_event_list

def post_processing(input_dir):
    for file in os.listdir(input_dir):
        if not file.endswith('.ann'):
            continue
        result = replace_discontinuous_event_with_its_head(input_dir+file)
        output = str()
        for tmp in result:
            output += str(tmp.textbound) + '\n'
            output += str(tmp) + '\n'
        with open(input_dir+file, 'w') as f:
            f.write(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, metavar='str', default='../brat_data/brat_data/input/',
                        help="input directory")
    args = parser.parse_args()
    
    print('Remove discontinuous events ...')
    post_processing(args.input)