import json
import csv
import re
import os
import sys

from bs4 import BeautifulSoup

def preprocess(data, ids, output_path):
    skipfiles = ['2312', '180311', '10849', '12131', '331652', '3330', 
             '337447', '117228', '346173', '44921', '55517', '55823', 
             '55865', '55869', '77152', '77250', '77514', '115616', 
             '3293', '3567', '3975', '44509', '53853', '54059', 
             '65041', '65318', '65384', '75032', '75884', '76576', '53787']
    tel_nums = ['13860', '48495', '68124', '73094', '73267', '73337', '73417', 
            '104183', '117190', '127220', '315259']
    emptyfile = ['217205']
    
    for doc in data:
        id_ = doc['id']
        if str(id_) in ids \
            and (id_ not in skipfiles) \
            and (id_ not in emptyfile) \
            and (id_ not in tel_nums): 
            
            id_ = doc['id']
            original_text = doc['text']
            body = BeautifulSoup(original_text, 'lxml')
            galleries = body.find_all('gallery')
            body = body.text
            if len(galleries) != 0:
                for g in galleries:
                    b0dy = body.replace(g.text, '')
            body = body.replace('&ndash;', '-'). replace('&mdash;', '-').replace('&nbsp;', ' ')
            body = body.replace('—', '-').replace('–', '-')
            body = body.replace(' & ', '&').replace('&', ' & ')
            body = body.replace('. . .', '').replace('. .', '.')
            matches = re.findall('\(\d+\) \d+\-\d+', body)  # e.g., (612) 871-7676
            for match in matches:
                replacement = match.replace('(', '').replace(')', '').replace(' ', '-')
                body = body.replace(match, replacement)
            
            output = dict()
            output['body'] = body

            with open(output_path+'/'+id_+'.json', 'w') as f:
                json.dump(output, f)


if __name__ == "__main__":
    input_file = './data/wikinews_similar_v3.json'
    id_file = './data/wikinews_docs_totag.txt'
    output_path = './data/cdec_wikinews_v3/json/'
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    with open(id_file, 'r') as f:
        ids = f.readlines()
    ids = [id_.strip() for id_ in ids]
    
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    
    preprocess(data, ids, output_path)