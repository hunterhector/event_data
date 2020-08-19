# Now in the second pipeline, we start to create document pairs.
# Assume we know the pair names.
import os

from forte.pipeline import Pipeline
from forte.processors.writers import PackNameMultiPackWriter

from processors.coref_propose import SameLemmaSuggestionProvider
from processors.evidence_questions import QuestionCreator
from readers.event_reader import TwoDocumentPackReader
from utils import set_logging

set_logging()

pairs = [('00_Abstract.json', '01_Abstract.json')]

pair_pipeline = Pipeline()
pair_pipeline.set_reader(TwoDocumentPackReader())

# Create event relation suggestions
pair_pipeline.add(SameLemmaSuggestionProvider())

# Create coreference questions
pair_pipeline.add(QuestionCreator())

# Write out the events.
input_path = os.path.join('sample_data', 'event_detected')
output_path = os.path.join('sample_data', 'pairs')

pair_pipeline.add(
    PackNameMultiPackWriter(), {
        'output_dir': output_path,
        'indent': 2,
        'overwrite': True,
        'drop_record': True
    })

pair_pipeline.initialize()
pair_pipeline.run(input_path, pairs)