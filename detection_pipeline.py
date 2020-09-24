import os

from forte.pipeline import Pipeline
from forte.processors.stanfordnlp_processor import StandfordNLPProcessor
from forte.processors.writers import PackNameJsonPackWriter
from processors.combined_processor import LemmaJunNombankOpenIEEventDetector
# from processors.openie_processor import AllenNLPEventProcessor
from readers.event_reader import DocumentReader, DocumentReaderJson
from utils import set_logging
import spacy

nlp = spacy.load("en_core_web_sm")

set_logging()

# file paths
# coling2018_path = './sample_data/output_from_coling2018_event/'
# coling2018_path = './data/kairos_cdec_candidates/output_from_coling2018_event/'
coling2018_path = './data/data/cdec_wikinews_v3/all_articles_v2/'

# In the first pipeline, we simply add events and some annotations.
detection_pipeline = Pipeline()
# Read raw text.
detection_pipeline.set_reader(DocumentReaderJson())

# Call stanfordnlp.
detection_pipeline.add(StandfordNLPProcessor())

# Call the event detector.
detection_pipeline.add(LemmaJunNombankOpenIEEventDetector(jun_output=coling2018_path, tokenizer=nlp))
# detection_pipeline.add(AllenNLPEventProcessor())

# Write out the events.
# input_path = os.path.join('sample_data', 'raw_text')
# output_path = os.path.join('sample_data', 'event_detected')
# input_path = os.path.join('data/kairos_cdec_candidates', 'raw_kairos_cdec_candidates')
# output_path = os.path.join('output/data', 'kairos_cdec_candidates')
input_path = os.path.join('./data/cdec_wikinews_v3', 'raw_all_articles_v2')
output_path = os.path.join('output/data', 'cdec_wikinews_v3_pruned_nombank_Sep24')
# input_path = os.path.join('./data/debug', 'input')
# output_path = os.path.join('data/debug', 'output')

detection_pipeline.add(
    PackNameJsonPackWriter(), {
        'output_dir': output_path,
        'indent': 2,
        'overwrite': True,
        # 'drop_record': True
    })

detection_pipeline.initialize()

detection_pipeline.run(input_path)
