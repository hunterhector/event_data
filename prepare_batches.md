# Batch Wikinews

To create document batches, run the following in the root directory (`event_data/`).

## Download data

```bash
mkdir -p cdec_wikinews data
```

Download `wikinews-1220-similar.json` and `coling2018_out` from [drive](https://drive.google.com/drive/folders/1VbL3KROxgBhkyW6b8rQ0NMJC2qsHO4C5?usp=sharing) to `cdec_wikinews/`.

Also download the folder `topics` from [drive](https://drive.google.com/drive/folders/1-hgRDCB0EFsyqs6JGQ8pED_N_yxRDAsV?usp=sharing) to `data/`.

## Prepare batches

Also check [prepare_batches.sh](prepare_batches.sh) for the corresponding shell script.

```bash
# set batch ID
export EVENT_BATCH_ID=1
export BATCH_NUM=batch${EVENT_BATCH_ID}
```

Pick 5 document groups from the two major categories (Disasters and Accidents, Politics and Conflicts).

```bash
let "SED_START_IDX = (${EVENT_BATCH_ID} - 1) * 5 + 1"
let "SED_END_IDX = ${EVENT_BATCH_ID} * 5"
mkdir -p data/${BATCH_NUM}
sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Disasters_and_accidents.ids.txt > data/${BATCH_NUM}/doc_clusters.txt
sed -n "${SED_START_IDX}, ${SED_END_IDX}p" data/topics/Politics_and_conflicts.ids.txt >> data/${BATCH_NUM}/doc_clusters.txt
```

Create a directory with corresponding raw document files, as well as outputs from Araki et al., 2018.

```bash
python prepare_doc_batch.py \
    --wikinews cdec_wikinews/wikinews-0121-similar.json \
    --coling2018 cdec_wikinews/coling2018_out \
    --doc-clusters data/${BATCH_NUM}/doc_clusters.txt \
    --out cdec_wikinews/${BATCH_NUM}
```

Run the event detection pipeline and convert documents into `DataPack` format.

```bash
python detection_pipeline.py \
    --dir cdec_wikinews/${BATCH_NUM} \
    --coling2018 cdec_wikinews/${BATCH_NUM}/coling2018_out
```

Here, detected events are manually corrected by uploading to Stave single-doc server.
Extract `packs` from the resulting .sqlite3 database before creating multi-packs.

```bash
python load_stave_single-doc.py \
    --sql ${STAVE_DB_PATH} \
    --project-name cdec_${BATCH_NUM} \
    --doc-clusters data/${BATCH_NUM}/doc_clusters.txt \
    --out ${BATCH_OUT_PATH}/packs
```

Use the document cluster information to create `MultiPack` files. Currently, we only use cliques (aka document groups) of upto size 4. The skipped cliques are written to `cdec_wikinews/${BATCH_NUM}/doc_clusters_skipped.txt`. Potentially, we can get back to these larger cliques at the end of AMT process.

```bash
python pair_pipeline.py \
    --dir cdec_wikinews/${BATCH_NUM} \
    --doc-pairs data/${BATCH_NUM}/doc_clusters.txt \
    --clique-threshold 4
```
