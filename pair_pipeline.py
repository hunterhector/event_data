# Now in the second pipeline, we start to create document pairs.
# Assume we know the pair names.
import os
import argparse
import itertools
from pathlib import Path

from forte.pipeline import Pipeline
from forte.processors.writers import PackNameMultiPackWriter

from processors.coref_propose import SameLemmaSuggestionProvider
from processors.evidence_questions import QuestionCreator
from readers.event_reader import TwoDocumentPackReader
from utils import set_logging


def read_doc_pairs(inp_path, max_size: int, out_dir: Path):
    doc_pairs = []
    out_path = out_dir / "doc_clusters.txt"
    out_path_skipped = out_dir / "doc_clusters_skipped.txt"
    with open(out_path, "w") as wf, open(out_path_skipped, "w") as wf_skipped:
        with open(inp_path, "r") as rf:
            for line in rf:
                group_docs = line.strip().split()
                if len(group_docs) <= max_size:
                    for doc1, doc2 in itertools.combinations(group_docs, 2):
                        doc_pairs.append((f"{doc1}.json", f"{doc2}.json"))
                    wf.write(line)
                else:
                    wf_skipped.write(line)

    return doc_pairs


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="generate MultiPack using pre-defined document pairs"
    )
    parser.add_argument(
        "--dir", type=Path, default="data", help="source directory path for Packs"
    )
    parser.add_argument(
        "--doc-pairs", type=str, help="path to the file with document pairs"
    )
    parser.add_argument(
        "--clique-threshold", type=int, default=4, help="max size of clique to use"
    )

    args = parser.parse_args()

    set_logging()

    # reading pre-selected document pairs
    pairs = read_doc_pairs(args.doc_pairs, args.clique_threshold, args.dir)
    print(f"# document pairs: {len(pairs)}")

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
        {
            "output_dir": str(output_path),
            "indent": 2,
            "overwrite": True,
            "drop_record": True,
        },
    )

    pair_pipeline.initialize()
    pair_pipeline.run(str(input_path), pairs)
