"""
This file contains a function for the mask-out idea
"""

import os
import sys
import json
import argparse
from copy import deepcopy

sys.path.insert(0, os.path.abspath(".."))

from forte.data.data_pack import DataPack
import spacy

nlp = spacy.load("en_core_web_md")

suffixes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

def split4maskout(pack):
    count_target = 0
    min_num_events = 7  # hyperparameter
    
    max_tokens = 300  # just a sample
    
    text = pack['py/state']['_text']
    doc = nlp(text)
    
    one_pack_is_enough = False
    for i in range(10):
        
        num_split = int(len(doc) / (max_tokens + 50*i)) + 1

        # skip if short document, i.e, no need for split: one pack is enough
        if num_split == 1:
            one_pack_is_enough = True
            break
        
        # adjust split boundaries so that splitting is done evenly
        actual_max_token = int(len(doc) / num_split)

        # find boundary indices based on sentence
        next_boundary = actual_max_token
        boundary_indices = []
        for sent in doc.sents:
            if (sent.start) < next_boundary <= (sent.end):
                boundary_indices.append(sent.end_char)
                next_boundary += actual_max_token

        # split events into different packs
        groups = [[] for i in boundary_indices]
        count_events = 0
        event_dict = {}
        for annotation in pack['py/state']['annotations']:
            if annotation['py/object'] == 'edu.cmu.EventMention':
                event_dict[annotation['py/state']['_span']['begin']] = annotation
                count_events += 1
            else:
                # store all annnotation other than event annotation 
                for group in groups:
                    group.append(annotation)
        
        # note: the annotation is not ordered by index after manual correction
        num_events_per_group = [0 for i in boundary_indices]
        current_group = 0
        for position in sorted(event_dict):
            if position < boundary_indices[current_group]:
                groups[current_group].append(event_dict[position])
                num_events_per_group[current_group] += 1
            else:
                current_group += 1
                groups[current_group].append(event_dict[position])
                num_events_per_group[current_group] += 1

        # check if all group has events
        too_small_num_events = False
        for num in num_events_per_group:
            if 0 < num < min_num_events:
                too_small_num_events = True

        if too_small_num_events:
            # repeat this process with bigger max token length 
            # so that each group contains more than {min_num_events} events
            pass
        else:
            # break this loop because every group contains more than 5 events
            # or some groups contains no events
            break
    
    packs = []
    if one_pack_is_enough:
        packs.append(pack)
    else:
        # change only pack['py/state']['annotations'] in each file
        for idx, group in enumerate(groups):
            new_pack = deepcopy(pack)
            new_pack['py/state']['annotations'] = group
            packs.append(new_pack)
    
    return packs
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_corrected", type=str, help="directory path to the corrected Packs")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing output packs")
    
    args = parser.parse_args()
    
    for idx, file in enumerate(os.listdir(args.pack_corrected)):
        
        if not os.path.isfile(args.pack_corrected+file):
            continue
        
        skip = False
        for suffix in suffixes:
            if suffix in file:
                skip = True
        if skip:
            continue
#         if '-' in file:  # skip splitted files
#             continue
        
        with open(args.pack_corrected+file, "r") as f:
            pack = json.load(f)
        
        packs = split4maskout(pack)
        
        print(f"{file}: len {len(packs)}")
        if len(packs) == 1:
            # no need to change file
            pass
        else:
            for idx, new_pack in enumerate(packs):
                new_pack_name = f"{file[:-5]}{suffixes[idx]}"
                out_path = f"{args.pack_corrected}{new_pack_name}.json"
                if os.path.isfile(out_path) and not args.overwrite:
                    print(f"pack {file[:-5]}{suffixes[idx]} already exists in the output folder, skipping!")
                    continue
                elif args.overwrite:
                    print(f"overwriting pack {file[:-5]}{suffixes[idx]}")
                
                with open(out_path, "w+") as f:
                    # Note: PackNameMultiPackWriter() refers this element for pack_name
                    new_pack['py/state']['meta']['py/state']['pack_name'] = new_pack_name
                    json.dump(new_pack, f, indent=4)