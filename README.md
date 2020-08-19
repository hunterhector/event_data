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
cd forte
pip install -e .
```

## Run Event Detection
Now you can run the script to check out the sample data:
```bash
python detection_pipeline.py
```

## Create Event Pairs
Now you can run the script to find the pairs:
```bash
python pair_pipeline.py
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
