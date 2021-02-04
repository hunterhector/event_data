#!/usr/bin/python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from tinydb import TinyDB, Query
from tinydb.operations import increment
from forte.data.readers.stave_readers import StaveMultiDocSqlReader

class SNSHandleRequests(BaseHTTPRequestHandler):
    """
    This class creates a simple request handler for aws_sns_topic subscriptions.
    """
    def __init__(self, stave_db_path, mace_code_path, mturk_db_path):
        self.stave_db_path = stave_db_path
        self.mace_code_path = mace_code_path
        self.mturk_db_path = mturk_db_path

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write("received get request")
        
    def do_POST(self):
        '''Reads post request body'''
        self._set_headers()
        content_len = int(self.headers.get('content-length', 0))
        post_body = json.loads(self.rfile.read(content_len).decode('utf-8'))
        self._handle_incoming_sns_notification(post_body)

    def do_PUT(self):
        self.do_POST()
    
    def _handle_incoming_sns_notification(self, body_obj):
        #parse input json obj for info
        msg_obj = json.loads(body_obj["Message"])["Events"][0]
        HIT_id = msg_obj['HITId']
        worker_id = msg_obj['WorkerId']
        answer_html = msg_obj['Answer']
        start_index = answer_html.find("<FreeText>")+len("<FreeText>")
        end_index = answer_html.find("</FreeText>")
        participant_code = answer_html[start_index:end_index]

        db = TinyDB(self.mturk_db_path)
        stack_target_table = db.table('stack_target')
        past_task_table = db.table('past_tasks')
        logging_table = db.table('logging')

        #query stack_target to get current rnd_number
        if (len(stack_target_table) != 0):
            record = stack_target_table.all()[-1]
            rnd_num = record['round_number']
            #if (last_record['completed']):
            #query past_task_table with specific round_number
            assignment_query = Query()
            rnd_assignments = past_task_table.update(
                { "completed": True, "annotator_id": worker_id},
                ((assignment_query.round_number == rnd_num) 
                    & (assignment_query.HITID == HIT_id))
                )
            logging_table.insert({"action":"hit_completed", 
                'log':"HITID:%s;worker:%s" % (HIT_id, worker_id)})

            rnd_assignments = stack_target_table.update(
                increment("completed_hit_count"),
                (assignment_query.round_number == rnd_num)   
            )

            if ((record['completed_hit_count']+1) >= record['sent_hit_count']):
                print("round %.1f complete" % rnd_num)
                rnd_assignments = stack_target_table.update(
                    {"completed" : True},
                    (assignment_query.round_number == rnd_num)   
                )
                logging_table.insert({"action":"rnd_completed", 
                    'log':"round %.1f" % (rnd_num)})
                
                #call collect data from processor & run MACE
                pipeline = Pipeline()
                pipeline.set_reader(StaveMultiDocSqlReader(), config={
                    'stave_db_path': self.stave_db_path
                })
                pipeline.add(MaceFormatCollector(self.mace_code_path))
                pipeline.run()
                

if __name__ == "__main__":
    PORT = 8989
    handler = partial(SNSHandleRequests, sys.argv[1], sys.argv[2], sys.argv[3])
    server = HTTPServer(("", PORT), handler)
    print("serving at port", PORT)
    server.serve_forever()
