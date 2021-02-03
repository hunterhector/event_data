import sys, os
import hashlib
import argparse
import sqlite3

from tinydb import TinyDB, Query

from forte.pipeline import Pipeline
from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor
from forte.data.readers.stave_readers import StaveMultiDocSqlReader
sys.path.insert(0, os.path.abspath('..'))


class SeedCollector(MultiPackProcessor):
    """
    This is a class to collect multipack docs and save 
    in the db used in the annotator module
    """
    ROUND_DOC_TABLE_NAME = "round_doc"

    def __init__(self, stave_db_path, annotation_module_db_path, is_adding_multipack=False):
        #remove!!!
        self.stave_db_path = stave_db_path
        #END remove
        if not annotation_module_db_path.endswith("db.json"):
            annotation_module_db_path = annotation_module_db_path+os.path.sep+"db.json"
        self.db = TinyDB(annotation_module_db_path)
        self.round_doc_table = self.db.table(self.ROUND_DOC_TABLE_NAME)
        if (len(self.round_doc_table) == 0):
            #input seed
            self.seeds = []
            self.is_adding_seed = True
        self.is_adding_multipack = is_adding_multipack
        self.cur_index = 0

        #process stave_db to contain a hash field
        self._preprocess_stave_db()


        
    def _preprocess_stave_db(self):
        #connection = sqlite3.connect(self.config.stave_db_path)
        connection = sqlite3.connect(self.stave_db_path)
        connection.row_factory = sqlite3.Row
        cursor = connection.execute('SELECT * FROM nlpviewer_backend_crossdoc;')
        rows = cursor.fetchall()
        row_keys = rows[0].keys()
        if ('nameHash' not in row_keys):
            cursor.execute("""ALTER TABLE nlpviewer_backend_crossdoc ADD COLUMN nameHash CHAR(200);""")
        sql_update_query = """Update nlpviewer_backend_crossdoc set nameHash = ? where name = ?"""
        for row in rows:
            hashed = hashlib.sha256(str.encode(row["name"])).hexdigest()
            cursor.execute(sql_update_query, (hashed, row["name"]))
        connection.commit()
        cursor.close()
        #print("pre_process db completed")
        return


    def _process(self, input_pack: MultiPack):
        
        #get hash name
        hashed = hashlib.sha256(str.encode(input_pack.pack_name)).hexdigest()

        #For each row with annotation treat as seed 
        if (self.is_adding_seed): #first round adding seeds to round 0 and insert other as -1
            index, round_num = -1, -1
            for _ in input_pack.get_all_creator():
                index, round_num = self.cur_index, 0
                self.cur_index += 1
                break
            self.round_doc_table.insert({'name':input_pack.pack_name, "hashed":hashed, \
                "round_assigned":round_num, 'index':index, 'pack_names':input_pack._pack_names})
            
        elif (self.is_adding_multipack): #add additional docs into db if needed
            #check whether current multipack name already in db
            query = Query()
            if (self.round_doc_table.search(query.name == input_pack.pack_name) == []):
                self.round_doc_table.insert({'name':input_pack.pack_name, "hashed":hashed,\
                    "round_assigned":-1, 'index':-1, 'pack_names':input_pack._pack_names})
        

if __name__ == '__main__':
    #db_path = sys.argv[1]
    #tiny_db_path = sys.argv[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--add_doc", help="adding more multidocs",
                    action="store_true")
    parser.add_argument("stave_db_path", type=str,
                    help="path to the stave sqlite database")
    parser.add_argument("annotator_db_path", type=str, default="./db.json",
                    help="path to the db.json file for annotator module")
    options = parser.parse_args()  
    is_adding_multipack = True if options.add_doc else False

    pipeline = Pipeline()
    pipeline.set_reader(StaveMultiDocSqlReader(), config={
        'stave_db_path': options.stave_db_path
    })
    pipeline.add(SeedCollector(options.stave_db_path, options.annotator_db_path, is_adding_multipack=is_adding_multipack))
    pipeline.run()
