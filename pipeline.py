import logging
import os, glob, itertools

from forte.data.selector import AllPackSelector
from forte.pipeline import Pipeline
from forte.processors.stanfordnlp_processor import StandfordNLPProcessor
from forte.processors.writers import PackNameMultiPackWriter

from coref_propose import SameLemmaSuggestionProvider, EmbeddingSimilaritySuggestionProvider
from event_detector import SameLemmaEventDetector, LemmaMatchAndCOLING2018OEDEventDetector
from evidence_questions import QuestionCreator
from pseudo_answer import ExampleQuestionAnswerer
from readers.event_reader import TwoDocumentPackReader

# input_path = 'brat_data/input'
# output_path = 'brat_data/output'
# input_path = 'brat_data/input_'
# output_path = 'brat_data/output_'
# input_path = 'sample_data/input'
# output_path = 'sample_data/output'
# input_path = './data/output/data/cdec_wikinews_processed/GROUP-104/'
# output_path = './output/data/cdec_wikinews_processed/GROUP-104/'
input_dir = './data/output/data/cdec_wikinews_processed/'
output_dir = './output/data/cdec_wikinews_processed/'

for dir_ in os.listdir(input_dir):
    input_path = input_dir+dir_+'/'
    output_path = output_dir+dir_+'/'
    print('input path:', input_path)
    print('output_path:', output_path)
    

    pl = Pipeline()
    # Read raw text.
    pl.set_reader(TwoDocumentPackReader())

    # Call stanfordnlp
    pl.add(StandfordNLPProcessor(), selector=AllPackSelector())

    # Call the event detector
    # pl.add(SameLemmaEventDetector(event_lemma_list_filename="./lemma_match/event_lemma.txt"), selector=AllPackSelector())
    pl.add(LemmaMatchAndCOLING2018OEDEventDetector(event_lemma_list_filename="./lemma_match/event_lemma.txt", coling2018_event_output_path=input_path), selector=AllPackSelector())

    # Create event relation suggestions
    pl.add(EmbeddingSimilaritySuggestionProvider())

    # Create coreference questions
    pl.add(QuestionCreator())

    # Answer the questions
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
    # pairs = [('00_Abstract', '01_Abstract')]  # sample data
    all_files_w_ext = list(map(lambda x: os.path.basename(x), glob.glob(os.path.join(input_path, "*.txt"))))
    all_files_wo_ext = list(map(lambda x: os.path.splitext(x)[0], all_files_w_ext))
    pairs = itertools.combinations(all_files_wo_ext, 2)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )

    print('start pipeline')
    pl.run(input_path, pairs)
    break  # todo: to be removed
