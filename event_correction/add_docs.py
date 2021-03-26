import argparse
import sqlite3
from tinydb import TinyDB, where
from pathlib import Path


def add_pack(
    name: str, textPack: str, ontology: str, db_path: Path, project_name: str = None, overwrite: bool = False,
):
    """
    add new pack into single doc stave
    """
    con = sqlite3.connect(db_path)
    cursor = con.cursor()

    # searching for document in the db
    result = cursor.execute(
        "SELECT * FROM nlpviewer_backend_document WHERE name=:pack_name", {"pack_name": name},
    ).fetchone()
    if result is not None:
        if overwrite:
            print("warning! overwriting pack %s in the db, you will lose the previous work" % name)
        else:
            print("pack %s already exists in the db, skipping" % name)
            pack_id = result[0]
            return pack_id

    if project_name is None:
        print("adding pack %s" % name)
        cursor.execute(
            "INSERT or REPLACE INTO nlpviewer_backend_document(name, textPack) VALUES(?,?)", (name, textPack),
        )
    else:
        # getting project id
        result = cursor.execute(
            "SELECT * FROM nlpviewer_backend_project WHERE name=:project_name",
            {"project_name": project_name},
        ).fetchone()
        if result is not None:
            # project exists
            project_id, _, _ = result
        else:
            # create new project
            print("creating project %s" % project_name)
            cursor.execute(
                "INSERT INTO nlpviewer_backend_project(ontology, name) VALUES(?,?)", (ontology, project_name)
            )
            project_id, _, _ = cursor.execute(
                "SELECT * FROM nlpviewer_backend_project WHERE name=:project_name",
                {"project_name": project_name},
            ).fetchone()

        print("adding pack %s to project %s" % (name, project_name))
        cursor.execute(
            "INSERT or REPLACE INTO nlpviewer_backend_document(name, textPack, project_id) VALUES(?,?,?)",
            (name, textPack, project_id),
        )

    result = cursor.execute(
        "SELECT * FROM nlpviewer_backend_document WHERE name=:pack_name", {"pack_name": name},
    ).fetchone()
    pack_id = result[0]

    con.commit()
    con.close()

    return pack_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="add new documents to stave single doc db")
    parser.add_argument("stave_db_path", type=Path, help="path to stave db")
    parser.add_argument("pack_db_path", type=Path, help="path to pack tinydb for scheduling")
    parser.add_argument("packs", type=Path, help="path to directory with packs")
    parser.add_argument("ontology", type=Path, help="path to ontology json")
    parser.add_argument("--url", type=str, help="URL prefix for stave")
    parser.add_argument("--out", type=Path, help="write stave links for docs in queue")
    parser.add_argument("--project", type=str, default=None, help="project name")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing files in the db")

    args = parser.parse_args()

    with open(args.ontology, "r") as rf:
        ontology = rf.read()

    db = TinyDB(args.pack_db_path)
    table = db.table("ongoing_table")

    with open(args.out, "w") as wf:
        for item_ in table.all():
            pack_name = item_["pack_name"]
            if not pack_name.endswith(".json"):
                pack_name += ".json"
            with open(args.packs / pack_name, "r") as rf:
                pack = rf.read()
            pack_id = add_pack(
                pack_name,
                pack,
                ontology,
                args.stave_db_path,
                project_name=args.project,
                overwrite=args.overwrite,
            )
            wf.write("%s/%s\n" % (args.url, pack_id))
