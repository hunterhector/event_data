#!/bin/bash

# Run COLING2018-event pipeline. 

DATA_PATH="../brat_data"
INPUT_DIR="../brat_data/input"
OUTPUT_DIR="../brat_data/output"
DATA_NAME="data"

# Stanford CoreNLP, create .json file for each input file
java -Xmx8g -cp "stanford-corenlp-full-2018-10-05/*" edu.stanford.nlp.pipeline.StanfordCoreNLP -props resources/corenlp.properties -file $INPUT_DIR -extension .txt -threads 4 -outputFormat json -outputDirectory $DATA_PATH

# Create empty .ann file for each input file
# python ../create_ann.py

# NLTK -- WordNet
python -m nltk.downloader wordnet
python -m nltk.downloader averaged_perceptron_tagger

# Polyglot
polyglot download morph2.en 


mkdir -p $OUTPUT_DIR

OUTPUT_PREPROCESS=$OUTPUT_DIR"/"$DATA_NAME".json.gz"

python preprocess.py --input $INPUT_DIR --output $OUTPUT_PREPROCESS

OUTPUT_WSD=$OUTPUT_DIR"/"$DATA_NAME"_wsd.json.gz"

python wsd.py --input $OUTPUT_PREPROCESS --output $OUTPUT_WSD 

OUTPUT_PHRASE=$OUTPUT_DIR"/"$DATA_NAME"_wsd_phrase.json.gz"

python phrase.py --input $OUTPUT_WSD --output $OUTPUT_PHRASE

OUTPUT_RULE=$OUTPUT_DIR"/"$DATA_NAME"_wsd_phrase_rule.json.gz"

python rule.py --input $OUTPUT_PHRASE --output $OUTPUT_RULE

OUTPUT_ANN2BRAT="./"

python ann2brat.py --input $OUTPUT_RULE --output $OUTPUT_ANN2BRAT

python ../postprocessing.py  --input $INPUT_DIR"/"