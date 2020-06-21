import logging
import os, glob, itertools

from forte.data.selector import AllPackSelector
from forte.pipeline import Pipeline
from forte.processors.stanfordnlp_processor import StandfordNLPProcessor
from forte.processors.writers import DocIdMultiPackWriter

from coref_propose import SameLemmaSuggestionProvider, EmbeddingSimilaritySuggestionProvider
from event_detector import SameLemmaEventDetector
from evidence_questions import QuestionCreator
from pseudo_answer import ExampleQuestionAnswerer
from readers.event_reader import TwoDocumentPackReader

# input_path = 'brat_data/input'
# output_path = 'brat_data/output'
input_path = 'sample_data/input'
output_path = 'sample_data/output'

pl = Pipeline()
# Read raw text.
pl.set_reader(TwoDocumentPackReader())

# Call stanfordnlp
pl.add(StandfordNLPProcessor(), selector=AllPackSelector())

# Call the event detector
pl.add(SameLemmaEventDetector(event_lemma_list_filename="event_lemma.txt"), selector=AllPackSelector())

# Create event relation suggestions
pl.add(EmbeddingSimilaritySuggestionProvider())

# Create coreference questions
pl.add(QuestionCreator())

# Answer the questions
# pl.add(ExampleQuestionAnswerer())

pl.add(
    DocIdMultiPackWriter(), {
        'output_dir': output_path,
        'indent': 2,
        'overwrite': True,
        'drop_record': True
    })

pl.initialize()

# Here we specify the pairs of documents to be used.
# pairs = [('00_Abstract', '01_Abstract')]  # sample data
all_files_w_ext = list(map(lambda x: os.path.basename(x), glob.glob(os.path.join(input_path, "*.txt"))))
all_files_wo_ext = list(map(lambda x: os.path.splitext(x)[0], all_files_w_ext))
pairs = itertools.combinations(all_files_wo_ext, 2)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

pl.run(input_path, pairs)
