import os
import logging

from forte.data.selector import AllPackSelector
from forte.pipeline import Pipeline
from forte.processors.stanfordnlp_processor import StandfordNLPProcessor
from forte.processors.writers import PackNameMultiPackWriter

from coref_propose import SameLemmaSuggestionProvider
from event_detector import EventDetector
from evidence_questions import QuestionCreator
from readers.event_reader import TwoDocumentPackReader

input_path = os.path.join('sample_data', 'input')
output_path = os.path.join('sample_data', 'output')

pl = Pipeline()
# Read raw text.
pl.set_reader(TwoDocumentPackReader())

# Call stanfordnlp
pl.add(StandfordNLPProcessor(), selector=AllPackSelector())

# Call the event detector
pl.add(EventDetector(), selector=AllPackSelector())

# Create event relation suggestions
pl.add(SameLemmaSuggestionProvider())

# Create coreference questions
pl.add(QuestionCreator())

# # Answer the questions
# pl.add(ExampleQuestionAnswerer())

pl.add(
    PackNameMultiPackWriter(), {
        'output_dir': output_path,
        'indent': 2,
        'overwrite': True,
        'drop_record': True
    })

pl.initialize()

# Here we specify the pairs of documents to be used.
pairs = [('00_Abstract', '01_Abstract')]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

pl.run(input_path, pairs)
