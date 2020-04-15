# event_data

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

## Update Ontology
You can modify the `event_ontology.json` file to create new types of add new 
features. After you finished the file, at the project's root directory, run
the following:
```bash
generate_ontology create -i event_ontology.json -o . -r
```
This command means: generate the ontology using `event_ontology.json` as input,
and current directory `.` as output path. You should find a folder named `edu`
in the directory, it contains the generated code.

To fully understand the generation code, read [here](https://asyml-forte.readthedocs.io/en/latest/ontology_generation.html#).

## Create Some Data
Now you can run the script to check out the sample data:
```bash
python pipeline.py
```

