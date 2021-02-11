#!/usr/bin/python3
import boto3
from tinydb import TinyDB, Query
import sys
import sqlite3
import hashlib
#need file credentials.py
#need file .yaml? for configuration --- include 

from credentials import (MTURK_ACCESS_KEY, MTURK_SECRET_KEY, SNS_TOPIC_ID,
    MTURK_EVENT_BLOCKED_QUAL_ID)


class CrowdSourceAnnotationModule:
    """
    This class is used for .....
    """
    STACK_TABLE_NAME = 'stack_target'
    PAST_TASKS_TABLE_NAME = 'past_tasks'
    LOGGING_TABLE_NAME = "logging"
    ROUND_DOC_TABLE_NAME = "round_doc"
    MTURK_SANDBOX = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
    ANNOTATOR_GROUP_DESCRIPTION = "hello this is a place holder"
    STAVE_LINK = "http://miami.lti.cs.cmu.edu:8004/?tasks=%s&%s" #two pairs?
    MTURK_REQRMT_NUM_HITS_COMPLETED = 1000
    MTURK_REQRMT_PERCENT_APPROVAL_RATE = 95
    MTURK_HIT_LAYOUT_ID = "3BC45DRD9A1JXYGP43Y9NFLSKGQV7G"
    

    def __init__(self, stave_db_path, mturk_db_path):  # config_file?
        #read input files
        self.stave_db_path = stave_db_path
        self.number_of_copys = 3
        self.participant_criterion = {}
        self.screened_participants = []  #list of participantIDs
        self.task_distributor = [] #could take several formats
        self.is_sandbox_testing = True
        self.debug_flag = True
        db = TinyDB(mturk_db_path) #store all part list
        self.stack_target_table = db.table(self.STACK_TABLE_NAME)
        self.past_task_table = db.table(self.PAST_TASKS_TABLE_NAME)
        self.logging_table = db.table(self.LOGGING_TABLE_NAME)
        self.round_doc_table = db.table(self.ROUND_DOC_TABLE_NAME)
        #region_name ???

        if (self.is_sandbox_testing):
            self.mturk_client = boto3.client(
                'mturk',
                aws_access_key_id = MTURK_ACCESS_KEY,
                aws_secret_access_key = MTURK_SECRET_KEY,
                region_name='us-east-1',
                endpoint_url = self.MTURK_SANDBOX  #this uses Mturk's sandbox 
            )
        else:
            self.mturk_client = boto3.client(
                'mturk',
                aws_access_key_id = MTURK_ACCESS_KEY,
                aws_secret_access_key = MTURK_SECRET_KEY,
                region_name='us-east-1',
            )
        #might need to load from static if groups created ahead
        base_query = Query()
        if (db.search(base_query.annotator_group_IDs.exists()) == []):
            self.annotator_group_IDs = self.create_annotator_groups()
            db.insert({'annotator_group_IDs': self.annotator_group_IDs})
        else:
            record = db.search(base_query.annotator_group_IDs.exists())[0]
            self.annotator_group_IDs = record['annotator_group_IDs']
        
        #load round_size from db or query seed set size from stave_db
        if (db.search(base_query.round_size.exists()) == []):
            #need to query for seed set size
            print(self.round_doc_table.search(base_query.round_assigned == 0))
            self.round_size = len(self.round_doc_table.search(base_query.round_assigned == 0))
            db.insert({'round_size': self.round_size})
        else:
            record = db.search(base_query.round_size.exists())[0]
            self.round_size = record['round_size']

    def create_annotator_groups(self, name="AnnotatorGroup_%02d", \
        description=ANNOTATOR_GROUP_DESCRIPTION):
        annotator_group_IDs = []
        for i in range(self.number_of_copys):
            try:
                response = self.mturk_client.create_qualification_type(
                    Name=(name%i),
                    Description=description,
                    QualificationTypeStatus='Active',
                )
                #TODO: try catch here?
                qual_id = response['QualificationType']['QualificationTypeId']
                annotator_group_IDs += [qual_id]
            except:
                e = sys.exc_info()[0]
                print(e)

        return annotator_group_IDs
    
    def add_qualification(self, qualification_id, worker_id, bool_send_not):
        response = self.mturk_client.associate_qualification_with_worker(
            QualificationTypeId=qualification_id,
            WorkerId=worker_id,
            IntegerValue=1,
            SendNotification=bool_send_not)
        return response

    '''
    def _load_docs_from_db(self):
        self.round_doc_table.insert({'name':row['name'], "hashed":hashed, "round_assigned":round_assigned})
        connection.commit()
        cursor.close()
        return list(zip(seed_hashed_pairs, first_round_pairs))
        '''

    def _get_annotation_pairs_for_round(self, round_num): 
        #step1 load the existing round
        query = Query()
        pre_pairs_dic, pairs = {}, []
        pre_pairs_hash_ordered = []
        for each in self.round_doc_table.search(query.round_assigned == (int(round_num)-1)):
            pre_pairs_dic[each['index']] = (each['hashed'], each['pack_names'])

        #if round# is X.2 then use the pairs as already determined/saved in db
        if (round_num * 10 % 2 == 0):
            #round docs already determined
            for each in self.round_doc_table.search(query.round_assigned == int(round_num)):
                pairs += [each['hashed']]
        else:
            #match new round of articles to the previous round (trying to maximize overlap)
            for i in range(self.round_size):
                pre_pairs_hash_ordered += [pre_pairs_dic[i][0]]
                def __contains_packs(pack_names, p1, p2):
                    all_pack_names = [p1, p2]
                    for pack in pack_names:
                        if pack in all_pack_names:
                            return True
                    return False
                results = self.round_doc_table.search((query.round_assigned == -1) & query.pack_names.test(__contains_packs,\
                     pre_pairs_dic[i][1][0], pre_pairs_dic[i][1][1]))
                if results != []:
                    #update selected to be the new round number
                    selected = results[0] #Optimization ---- now selected the 0th
                    self.round_doc_table.update({ "round_assigned": int(round_num), "index":i},
                    ((query.name == selected['name']) & (query.hashed == selected['hashed']))) 
                    pairs += [selected['hashed']]
                else: #does not exist --- fill with random later
                    pairs += [None]
            print('filled with overlapped pairs', pairs)
            #fill the None's with random selected
            for each in self.round_doc_table.search(query.round_assigned == -1):
                while (None in pairs):
                    none_index = pairs.index(None)
                    pairs[none_index] = each['hashed']
                    self.round_doc_table.update({ "round_assigned": int(round_num), "index":none_index},
                    ((query.name == each['name']) & (query.hashed == each['hashed'])))
                if (None not in pairs):
                    break
            print('all pairs', pairs)
        if (len(pairs) < len(pre_pairs_hash_ordered)):
            print("All pairs have been exhausted: last_batch size is" % len(pairs))
            return list(zip(pre_pairs_hash_ordered[:len(pairs)], pairs))
        return list(zip(pre_pairs_hash_ordered, pairs))


    def publish_hit(self, website_url, annotator_group_ID, is_first_round=False):
        # params include reward, title, keywords, description, maxassignments,
        # lifetime, AssignmentDurationInSeconds, QualificationRequirements, 
        # typeoflayout -
        HIT_DESCRIPTION = """You will be asked to read 2 pairs of news articles,
         and for each pair you will be asked to identify texts that refer to
         the same events."""

        qualification_requirements = [
                {	#location 
                    'QualificationTypeId': '00000000000000000071',
                    'Comparator': 'In',
                    'LocaleValues': [
                        {'Country': 'US'},  #canada "CA"  "GB" "NZ" "AU"
                        {'Country': 'CA'},
                    ],
                    'ActionsGuarded': 'PreviewAndAccept'
                },
                {	# # of hit approved > 30
                    'QualificationTypeId': '00000000000000000040',
                    'Comparator': 'GreaterThanOrEqualTo',
                    'IntegerValues': [self.MTURK_REQRMT_NUM_HITS_COMPLETED],
                    'ActionsGuarded':  'PreviewAndAccept'  #'Accept'|'DiscoverPreviewAndAccept'
                },
                { # approval percent
                    'QualificationTypeId': '000000000000000000L0',
                    'Comparator': 'GreaterThanOrEqualTo',
                    'IntegerValues': [self.MTURK_REQRMT_PERCENT_APPROVAL_RATE], 
                    'ActionsGuarded':  'PreviewAndAccept'

                },
                { #not in temporary block
                    'QualificationTypeId': MTURK_EVENT_BLOCKED_QUAL_ID,
                    'Comparator':"DoesNotExist",
                    'ActionsGuarded':"PreviewAndAccept"
                },
        ]
        if not is_first_round:
            # annotator groups are empty in the first round
            # annotators from other groups should not be allowed to do this task
            # i.e, only annotators with ID `annotator_group_ID` or new annotators are allowed
            disallowed_IDs = [
                x for x in self.annotator_group_IDs if x != annotator_group_ID]
            for group_ID in disallowed_IDs:
                qualification_requirements.append({ #who passed the annotator qualification
                    'QualificationTypeId': group_ID,
                    'Comparator': "DoesNotExist",
                        'ActionsGuarded':"PreviewAndAccept"
                    })
        new_hit = self.mturk_client.create_hit(
            MaxAssignments=1,  # required
            #AutoApprovalDelayInSeconds=3600*24,
            LifetimeInSeconds=3600*24,  # life time
            AssignmentDurationInSeconds=3600*24,  # time to complete the HIT
            Reward='2.4',  # string us dollar
            Title="Annotating Event Coreferences in News Articles",  #
            Keywords='annotation,event,news,coreference',
            Description=HIT_DESCRIPTION,
            QualificationRequirements=qualification_requirements,
            HITLayoutId=self.MTURK_HIT_LAYOUT_ID,
            HITLayoutParameters=[
                { 'Name': 'website_url',
                'Value': website_url},
        ])

        hit_type_id = new_hit['HIT']['HITTypeId']
        notification = {
            'Destination': SNS_TOPIC_ID,
            'Transport': 'SNS',
            'Version': '2014-08-15',
            'EventTypes': [
                'AssignmentSubmitted',
                # HITReviewable|AssignmentAccepted|AssignmentAbandoned|AssignmentReturned
                # AssignmentRejected|AssignmentApproved|HITCreated|HITExtended|HITDisposed|HITExpired
        ]}
        # Configure Notification settings using the HITTypeId 
        self.mturk_client.update_notification_settings(
            HITTypeId = hit_type_id,
            Notification = notification,
        )
        if (self.debug_flag): 
            print("https://workersandbox.mturk.com/mturk/preview?groupId="
                + new_hit['HIT']['HITGroupId'])
            print("HITID = " + new_hit['HIT']['HITId']
                + " (Use to Get Results)")
        return new_hit['HIT']['HITId'] 

    def run_round(self):
        if (self.debug_flag): print(self.logging_table.all())
        annotator_group_idx = 1
        is_first_round = False
        if (len(self.stack_target_table) == 0):
            #first round
            nxt_rnd_num = 1.1
            is_first_round = True
        else:
            last_record = self.stack_target_table.all()[-1]
            if (last_record['completed']):
                #all previous round completed ; start new round
                rnd_num_int = int(last_record['round_number'])
                rnd_num_frc = int(last_record['round_number'] * 10 % 10)
                if (rnd_num_int % 2 == 0):
                    if (rnd_num_frc == 1):
                        nxt_rnd_num = rnd_num_int + 0.2
                        annotator_group_idx = 2
                    else:  #rnd_num_frc == 2
                        annotator_group_idx = 0
                else:
                    #annotator_group_idx == 1
                    nxt_rnd_num = rnd_num_int + 1 + 0.1  
            else:
                #complete current round
                nxt_rnd_num = last_record['round_number']
                #TODO: under what circumstances would round not complete?
                print("last round# %.1f not finished" % nxt_rnd_num)
                return

        if (self.debug_flag): print("running round# %.1f" % nxt_rnd_num)
        annotation_pairs = self._get_annotation_pairs_for_round(nxt_rnd_num)
        print(annotation_pairs)
        print(self.round_doc_table.all())

        #publish tasks with #nxt_rnd_num, and take from the article pairs
        self.stack_target_table.insert({'round_number': nxt_rnd_num, 
            'completed':False, 'annotator_list':[], 'completed_hit_count':0, 
            "sent_hit_count":len(annotation_pairs)})
        for hash_pair in annotation_pairs:
            hit_id = self.publish_hit(self.STAVE_LINK % (hash_pair), 
                self.annotator_group_IDs[annotator_group_idx], is_first_round=is_first_round)
            hash_pair_str = "%s&%s" % hash_pair
            # additionally storing annotator group ID to assign the necessary qualification for new workers
            self.past_task_table.insert({'round_number':nxt_rnd_num, 
                                         'completed': False, 'hash_pair': hash_pair_str, 'HITID': hit_id,
                                         'annotator_group_ID': self.annotator_group_IDs[annotator_group_idx]})
            self.logging_table.insert({"action":"hit_created", 
                'log':"HITID:%s;hash_pair:%s" % (hit_id, hash_pair_str)})
        print(self.logging_table.all())
        return    



    

def _delete_db(mturk_db_path):
    db = TinyDB(mturk_db_path) #store all part list
    tables = ['stack_target', 'past_tasks', 'logging', 'round_doc']
    for t_name in tables:
        db.drop_table(t_name)

if __name__ == "__main__":
    stave_db_path = sys.argv[1]
    mturk_db_path = sys.argv[2]
    #_delete_db(mturk_db_path)
    mturk = CrowdSourceAnnotationModule(stave_db_path, mturk_db_path)
    mturk.run_round()
    #mturk.add_qualification("3PP3A267AC06C3I4KJZXPB0QD3UQ9X", "A2BH1DM1D62J5Q", True)
