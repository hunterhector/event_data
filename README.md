# Event Data

## Prerequisites
These codes are tested on Python 3.6 only.

To get started, install texar first.
```bash
pip install texar-pytorch
```

Install Forte:
```bash
git clone git@github.com:asyml/forte.git
# or git clone https://github.com/asyml/forte.git
cd forte
pip install -e .
```

Install open-domain event detection system (Araki and Mitamura, coling 2018):
```bash
git clone https://bitbucket.org/junaraki/coling2018-event.git
cd coling2018-event
```

Install python packages listed in coling2018-event/requirements.txt (Conda users)
```bash
conda env create --file myenv.yaml
```
or 
```bash
conda install -c anaconda nltk==3.3
conda install -c conda-forge beautifulsoup4
conda install -c conda-forge pattern==3.6
conda install -c conda-forge pyicu
pip install pycld2
conda install -c conda-forge morfessor==2.0.4
pip install polyglot
conda install -c conda-forge tqdm
pip install stanfordcorenlp


conda install -c conda-forge spacy
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md

conda install pytorch torchvision cudatoolkit=10.2 -c pytorch

pip install stanza

# for coling2018-event
conda install -c anaconda openjdk=8
```

Some modification in coling2018-event/preprocess.py:
```python
# l72~73
for dirpath, dirs, files in os.walk(input_dir):
    for f in files:
        txt_file = os.path.join(dirpath, f)
->
for f in os.listdir(input_dir):
    txt_file = os.path.join(input_dir, f)
```

## Create Some Data
Now you can run the script to check out the sample data:
```bash
mv run_coling2018-event.sh coling2018-event/run_coling2018-event.sh
cd coling2018-event
sh download.sh
sh run_coling2018-event.sh

cd ../
python pipeline.py
```

## To Start the Stave UI
We can now start using the UI, first obtain the Stave project:
```bash
git clone git@github.com:asyml/stave.git
```
Now you can start the system, first the front end:
```bash
yarn && yarn start
```
You will also need to start the back end:
```bash 
cd simple-backend
./start-dev.sh
```
You can start using the front end, as a development server,
the username/password pair is 'admin','admin'.

## Update Ontology
You can modify the `event_ontology.json` file to create new types of add new 
features. After you finished the file, at the project's root directory, run
the following:
```bash
generate_ontology create -i event_ontology.json -o . -m full.json -r
```
This command means: generate the ontology using `event_ontology.json` as input,
and current directory `.` as output path. You should find a folder named `edu`
in the directory, it contains the generated code. You can also find a file
called `full.json` that contains the ontology needed for the UI.

To fully understand the generation code, read [here](https://asyml-forte.readthedocs.io/en/latest/ontology_generation.html#).
