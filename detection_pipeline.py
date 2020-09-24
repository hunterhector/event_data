import os
import argparse
import spacy
from pathlib import Path

from forte.pipeline import Pipeline
from forte.processors.writers import PackNameJsonPackWriter

from processors.combined_processor import LemmaJunNombankOpenIEEventDetector
from processors.stanfordnlp_processor import StandfordNLPProcessor
from readers.event_reader import DocumentReaderJson

from utils import set_logging

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="run detection pipeline")
    parser.add_argument(
        "--dir",
        type=Path,
        default="data",
        help="input directory path, assumes json files under json/",
    )
    parser.add_argument(
        "--coling2018",
        type=str,
        default="./data/data/cdec_wikinews_v3/all_articles_v2/",
        help="path to events extracted using Jun's open-domain event extraction model",
    )

    args = parser.parse_args()

    nlp = spacy.load("en_core_web_sm")

    set_logging()

    # file paths
    coling2018_path = args.coling2018

    # In the first pipeline, we simply add events and some annotations.
    detection_pipeline = Pipeline()

    # Read raw text.
    detection_pipeline.set_reader(DocumentReaderJson())

    # Call stanfordnlp.
    detection_pipeline.add(StandfordNLPProcessor())

    # Call the event detector.
    detection_pipeline.add(
        LemmaJunNombankOpenIEEventDetector(jun_output=coling2018_path, tokenizer=nlp)
    )

    # Write out the events.
    input_path = args.dir / "json"
    output_path = args.dir / "packs"
    output_path.mkdir(exist_ok=True)

    detection_pipeline.add(
        PackNameJsonPackWriter(),
        {
            "output_dir": str(output_path),
            "indent": 2,
            "overwrite": True,
            # 'drop_record': True
        },
    )

    detection_pipeline.initialize()

    detection_pipeline.run(str(input_path))
