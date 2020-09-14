import logging
import os, glob, itertools

from forte.data.selector import AllPackSelector
from forte.pipeline import Pipeline
from forte.processors.stanfordnlp_processor import StandfordNLPProcessor
from forte.processors.writers import PackNameMultiPackWriter
from forte.processors.writers import PackNameJsonPackWriter

from coref_propose import SameLemmaSuggestionProvider, EmbeddingSimilaritySuggestionProvider
from event_detector import SameLemmaEventDetector, LemmaMatchAndCOLING2018OEDEventDetector
from evidence_questions import QuestionCreator
from pseudo_answer import ExampleQuestionAnswerer
from readers.event_reader import TwoDocumentPackReader
from readers.event_reader import DocumentReader
from utils import set_logging
import spacy
import sys

# input_path = 'brat_data/input'
# output_path = 'brat_data/output'
# input_path = 'brat_data/input_'
# output_path = 'brat_data/output_'
# input_path = 'sample_data/input'
# output_path = 'sample_data/output'
# input_path = './data/output/data/cdec_wikinews_processed/GROUP-104/'
# output_path = './output/data/cdec_wikinews_processed/GROUP-104/'
input_dir = './data/cdec_wikinews_v3/raw_all_articles_v2/'
input_dir = './data/cdec_wikinews_v3/files4debug/'

# input_dir = './data/cdec_wikinews_v3/raw_sample_articles/'
output_dir = './output/data/cdec_wikinews_v3_nombank/'
output_dir = './data/cdec_wikinews_v3/files4debug/'

df_file_path = './idf_table.json.gz'
lemma_list_path = "./lemma_match/event_lemma.txt"
coling2018_path = './data/data/cdec_wikinews_v3/all_articles_v2/'
nombank_path = './nombank_propositions.json'
# coling2018_path = './data/data/cdec_wikinews_v3/sample_articles/'
reporting_verbs = './reporting_verbs.txt'

## ------- ##
# working space
# similar to detection_pipeline.py
# note: 
#   - make sure that in the input_dir, there exist only .txt files
## ------- ##

set_logging()
nlp = spacy.load("en_core_web_sm")

# for dir_ in os.listdir(input_dir):
#     input_path = input_dir+dir_+'/'
#     output_path = output_dir+dir_+'/'
#     print('input path:', input_path)
#     print('output_path:', output_path)
#     if not os.path.isdir(input_path):
#         continue

input_path = input_dir
output_path = output_dir

pl = Pipeline()
# Read raw text.
pl.set_reader(DocumentReader())

# Call stanfordnlp
pl.add(StandfordNLPProcessor())

# Call the event detector
# pl.add(SameLemmaEventDetector(event_lemma_list_filename="./lemma_match/event_lemma.txt"), selector=AllPackSelector())
# pl.add(LemmaMatchAndCOLING2018OEDEventDetector(event_lemma_list_filename=lemma_list_path, coling2018_event_output_path=coling2018_path+dir_+'/', df_file=df_file_path, tokenizer=nlp))
pl.add(LemmaMatchAndCOLING2018OEDEventDetector( 
            event_lemma_list_filename=lemma_list_path, 
            coling2018_event_output_path=coling2018_path, 
            nombank_propositions=nombank_path, 
            df_file=df_file_path, 
            reporting_verbs=reporting_verbs, 
            tokenizer=nlp))

pl.add(
    PackNameJsonPackWriter(), {
        'output_dir': output_path,
        'indent': 2,
        'overwrite': True,
    })

print('Initializing ... ')
pl.initialize()  # maybe this is redundant???

print('Pipeline.run starts ...')
pl.run(input_path)
