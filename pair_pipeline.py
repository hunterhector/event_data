# Now in the second pipeline, we start to create document pairs.
# Assume we know the pair names.
import os
import sys
import argparse
import itertools
from pathlib import Path

from forte.pipeline import Pipeline
from forte.processors.writers import PackNameMultiPackWriter

from processors.coref_propose import SameLemmaSuggestionProvider
from processors.evidence_questions import QuestionCreator
from readers.event_reader import TwoDocumentPackReader
from utils import set_logging

suffixes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

def check_suffix(name):
    contain = False
    for suffix in suffixes:
        if suffix in name:
            contain = True
            
    return contain


def custom_combinations(dirpath, group_docs):
    """
    search files in out_dir / "packs/", and check if {doc}_* exists
    """
    pack_names = []
    for file in os.listdir(str(dirpath)+'/packs/'):
        if not os.path.isfile(str(dirpath)+'/packs/'+file):
            continue
        pack_names.append(file[:-5])
    
    # correct corresponding {doc}_* files if exist
    new_docs = [] 
    for doc in group_docs:
        splitted = []
        for pack in pack_names:
            if doc in pack:
                splitted.append(pack)
        if len(splitted) == 1:
            # no split
            new_docs += splitted
        elif len(splitted) > 1:
            splitted.remove(doc)
            new_docs += splitted

    temp_pairs = itertools.combinations(new_docs, 2)
    pairs = []
    for doc1, doc2 in temp_pairs:
        # remove pairs for the same document
        if check_suffix(doc1) and check_suffix(doc2):
            prefix_doc1 = doc1[:-1]
            prefix_doc2 = doc2[:-1]
            if prefix_doc1 == prefix_doc2:
                continue
        pairs.append((doc1, doc2))
    print(pairs)
    return pairs


def read_doc_pairs(inp_path, max_size: int, out_dir: Path):
    
    doc_pairs = []
    out_path = out_dir / "doc_clusters.txt"
    out_path_skipped = out_dir / "doc_clusters_skipped.txt"
    with open(out_path, "w") as wf, open(out_path_skipped, "w") as wf_skipped:
        with open(inp_path, "r") as rf:
            for line in rf:
                group_docs = line.strip().split()
                if len(group_docs) <= max_size:
                    # ToDo: replace this combination function w. customized one
                    pairs = custom_combinations(out_dir, group_docs)
                    for doc1, doc2 in pairs:
                        doc_pairs.append((f"{doc1}.json", f"{doc2}.json"))
                    wf.write(line)
                else:
                    wf_skipped.write(line)

    return doc_pairs


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="generate MultiPack using pre-defined document pairs")
    parser.add_argument("--dir", type=Path, default="data", help="source directory path for Packs")
    parser.add_argument("--doc-pairs", type=str, help="path to the file with document pairs")
    parser.add_argument("--clique-threshold", type=int, default=4, help="max size of clique to use")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing multipacks")

    args = parser.parse_args()

    set_logging()

    # reading pre-selected document pairs, considering splitted files
    pairs = read_doc_pairs(args.doc_pairs, args.clique_threshold, args.dir)
    print(f"# document pairs: {len(pairs)}")
    print(pairs)
#     sys.exit('force')
    pair_pipeline = Pipeline()
    pair_pipeline.set_reader(TwoDocumentPackReader())

    # Create event relation suggestions
    # pair_pipeline.add(SameLemmaSuggestionProvider())

    # Create coreference questions
    pair_pipeline.add(QuestionCreator())

    # Write out the events.
    input_path = args.dir / "packs"
    output_path = args.dir / "multipacks"
    output_path.mkdir(exist_ok=True)

    pair_pipeline.add(
        PackNameMultiPackWriter(),
        {"output_dir": str(output_path), "indent": 2, "overwrite": args.overwrite, "drop_record": True,},
    )

    pair_pipeline.initialize()
    pair_pipeline.run(str(input_path), pairs)
