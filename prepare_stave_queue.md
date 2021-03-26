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
