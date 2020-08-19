import os

from forte.pipeline import Pipeline
from forte.processors.stanfordnlp_processor import StandfordNLPProcessor
from forte.processors.writers import PackNameJsonPackWriter

# from processors.event_detector import KeywordEventDetector
from event_detector import KeywordEventDetector
from readers.event_reader import DocumentReader
from utils import set_logging

set_logging()

# In the first pipeline, we simply add events and some annotations.
detection_pipeline = Pipeline()
# Read raw text.
detection_pipeline.set_reader(DocumentReader())

# Call stanfordnlp.
detection_pipeline.add(StandfordNLPProcessor())

# Call the event detector.
detection_pipeline.add(KeywordEventDetector())

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