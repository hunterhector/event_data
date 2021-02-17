# Collecting MTurk annotations

## Requirements

1. tinydb
2. streamlit
3. matplotlib
4. numpy
5. pandas

## Quality control (MACE)

Refer to [SNSSimpleServer.py](SNSSimpleServer.py). This script is run indefinitely, so we can collect results in real time.

## Streamlit App: Tracking MTurk progress

Our streamlit app presents a quick summary of MTurk progress. The app can be found [here]().

### Updating database

We use TinyDB to keep track of assignments, workers and HITs. The database is stored as `mturk_progress.json`. To update the database run the following (to be run often). This connects to the MTurk account via API and collects latest information relating to our task.

```bash
# WARNING: remove the --sandbox option when using in production environment.
DB_PATH=mturk_progress.json
python update_mturk_progress.py \
    --db ${DB_PATH} \
    --sandbox
```

```bash
python streamlit_app.py \
    ${DB_PATH}
```
