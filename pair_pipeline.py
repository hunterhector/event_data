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


def read_doc_pairs(inp_path):
    doc_pairs = []
    with open(inp_path, "r") as rf:
        for line in rf:
            group_docs = line.strip().split("\t")
            for doc1, doc2 in itertools.combinations(group_docs, 2):
                doc_pairs.append((f"{doc1}.json", f"{doc2}.json"))
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

    args = parser.parse_args()

    set_logging()

    # reading pre-selected document pairs
    pairs = read_doc_pairs(args.doc_pairs)
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
