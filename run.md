# Batch Wikinews

To create document batches, run the following in the root directory (`event_data/`).

## Download data

```bash
mkdir -p cdec_wikinews data
```

Download `wikinews-1220-similar.json` and `coling2018_out` from [drive](https://drive.google.com/drive/folders/1VbL3KROxgBhkyW6b8rQ0NMJC2qsHO4C5?usp=sharing) to `cdec_wikinews/`.

Also download the folder `topics` from [drive](https://drive.google.com/drive/folders/1-hgRDCB0EFsyqs6JGQ8pED_N_yxRDAsV?usp=sharing) to `data/`.

## Prepare batches

```bash
# set batch ID
export EVENT_BATCH_ID=1
export BATCH_NUM=batch${EVENT_BATCH_ID}
```

```bash
let "SED_START_IDX = (${EVENT_BATCH_ID} - 1) * 5 + 1"
let "SED_END_IDX = ${EVENT_BATCH_ID} * 5"
mkdir -p data/${BATCH_NUM}
sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Disasters_and_accidents.ids.txt > data/${BATCH_NUM}/doc_clusters.txt
sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Politics_and_conflicts.ids.txt >> data/${BATCH_NUM}/doc_clusters.txt
```

```bash
python prepare_doc_batch.py \
    --wikinews cdec_wikinews/wikinews-0121-similar.json \
    --coling2018 cdec_wikinews/coling2018_out \
    --doc-clusters data/${BATCH_NUM}/doc_clusters.txt \
    --out cdec_wikinews/${BATCH_NUM}
```

```bash
python detection_pipeline.py \
    --dir cdec_wikinews/${BATCH_NUM} \
    --coling2018 cdec_wikinews/${BATCH_NUM}/coling2018_out
```

```bash
python pair_pipeline.py \
    --dir cdec_wikinews/${BATCH_NUM} \
    --doc-pairs data/${BATCH_NUM}/doc_clusters.txt
```