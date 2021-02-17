"""
Load .sqlite3 database from Stave single document interface.
This module updates DataPacks to use expert corrected events.
"""

import argparse
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
    parser.add_argument(
        "--project-name", type=str, help="target project name in SQL database"
    )
    parser.add_argument(
        "--doc-clusters",
        type=Path,
        required=True,
        help="path to doc clusters in the batch",
    )
    parser.add_argument(
        "--out", type=Path, help="directory path to write Packs",
    )
    args = parser.parse_args()

    set_logging()

    pipeline = Pipeline()
    # read from SQL database
    # target project name is passed as an argument
    reader_config = Config(
        {"stave_db_path": args.sql, "target_project_name": args.project_name},
        default_hparams=None,
    )
    pipeline.set_reader(StaveDataPackSqlReader(), config=reader_config)
    # write
    out_path = args.out
    out_path.mkdir(exist_ok=True, parents=True)
    pipeline.add(
        PackNameJsonPackWriter(),
        {"output_dir": str(out_path), "indent": 2, "overwrite": False},
    )
    pipeline.initialize()
    pipeline.run()
