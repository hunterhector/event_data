# Prepare queue for Event Correction and MTurk

## Corpus

Download packs from [Drive](https://drive.google.com/drive/folders/1j8RgIRBZf_tawwujZxHLG9ICX1a01Dsz?usp=sharing) to `cdec_wikinews/latest/`, and unzip the folder. Download the document groups for the topic from [Drive](https://drive.google.com/file/d/1sBoCfwzDKtRg9uavoSC57eVF43HXKtcA/view?usp=sharing) to `data/topics/`.

## DataPack DB

Download latest `db.sqlite3` for event correction from single doc Stave.
  
```bash
mkdir amt_data
cd event_correction
python update_pack_db.py \
    db.sqlite3 \
    ../amt_data/pack_tinydb.json
cd ..
```

## Update the queue

Update the above datapack DB using above scripts before updating the queue. The queue is currently set to a max size of 20.

```bash
bash prepare_stave_queue.sh single
```

## Adding docs to stave db

Add packs from the `ongoing_table` into the single doc stave db.

```bash
# (optional arguments)
# to specify project name, add the argument --project <PROJECT_NAME>
# to overwrite existing documents in the stave database, add the argument --overwrite. 
# Warning! --overwrite will remove any existing annotations for **all** packs in the ongoing table

cd event_correction
python add_docs.py \
    db.sqlite3 \
    ../amt_data/pack_tinydb.json \
    ../cdec_wikinews/latest/packs \
    ../full.json
```
