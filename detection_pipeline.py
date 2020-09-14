import os

from forte.pipeline import Pipeline
from forte.processors.stanfordnlp_processor import StandfordNLPProcessor
from forte.processors.writers import PackNameJsonPackWriter

from processors.event_detector import KeywordEventDetector
from processors.event_detector import LemmaJunNombankEventDetector
from processors.openie_processor import AllenNLPEventProcessor
from readers.event_reader import DocumentReader
from utils import set_logging
import spacy

nlp = spacy.load("en_core_web_sm")

set_logging()

# file paths
df_file_path = './tools/idf_table.json.gz'
lemma_list_path = "./tools/event_lemma.txt"
coling2018_path = './sample_data/output_from_coling2018_event/'
nombank_path = './tools/nombank_propositions.json'
reporting_verbs = './tools/reporting_verbs.txt'

# In the first pipeline, we simply add events and some annotations.
detection_pipeline = Pipeline()
# Read raw text.
detection_pipeline.set_reader(DocumentReader())

# Call stanfordnlp.
detection_pipeline.add(StandfordNLPProcessor())

# Call the event detector.
# detection_pipeline.add(KeywordEventDetector())
# detection_pipeline.add(LemmaJunNombankEventDetector(
#             event_lemma_list_filename=lemma_list_path, 
#             jun_output=coling2018_path, 
#             nombank_propositions=nombank_path, 
#             df_file=df_file_path, 
#             reporting_verbs=reporting_verbs, 
#             tokenizer=nlp))
detection_pipeline.add(AllenNLPEventProcessor())

# Write out the events.
input_path = os.path.join('sample_data', 'raw_text')
output_path = os.path.join('sample_data', 'event_detected')

detection_pipeline.add(
    PackNameJsonPackWriter(), {
        'output_dir': output_path,
        'indent': 2,
        'overwrite': True,
        # 'drop_record': True
    })

detection_pipeline.initialize()

detection_pipeline.run(input_path)
