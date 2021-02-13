import argparse
import sqlite3
from pathlib import Path

from forte.pipeline import Pipeline
from forte.common.configuration import Config
from forte.data.readers.stave_readers import StaveDataPackSqlReader
from forte.processors.writers import PackNameJsonPackWriter

from utils import set_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sql", type=str, help="path to read single document SQL database from stave"
    )
    parser.add_argument("--out", type=Path, help="directory path to write DataPack")
    args = parser.parse_args()

    set_logging()

    pipeline = Pipeline()
    # read from SQL database
    reader_config = Config({"stave_db_path": args.sql}, default_hparams=None)
    pipeline.set_reader(StaveDataPackSqlReader(), config=reader_config)
    # write
    out_path = args.out / "packs"
    out_path.mkdir(exist_ok=True)
    pipeline.add(
        PackNameJsonPackWriter(),
        {"output_dir": str(out_path), "indent": 2, "overwrite": True},
    )
    pipeline.initialize()
    pipeline.run()

