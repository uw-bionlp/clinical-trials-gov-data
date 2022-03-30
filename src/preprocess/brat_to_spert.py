import os
import sys
import json
import numpy as np
import random
import re
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils


regex_trailing_num = r'\d'

def clean_trailing_num(tp):
    if any(re.findall(regex_trailing_num, tp)):
        tp = re.sub(regex_trailing_num, '', tp)
    return tp

def write_json(data, file_path):
    with open(file_path, 'w+') as fout:
        json.dump(data, fout, ensure_ascii=False, indent=4)

def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
    sents_by_doc = [ ann.to_spert_format(debug=False) for ann in annotations ]

    spert, ents, rels = [], [], []
    for sents in sents_by_doc:
        for sent in sents:
            for e in sent["entities"]:
                e["type"] = clean_trailing_num(e["type"])
                ents.append(e['type'])
            for r in sent["relations"]:
                r["type"] = clean_trailing_num(r["type"])
                rels.append(r['type'])
        spert += sents
    
    ents = [ clean_trailing_num(e) for e in ents ]
    rels = [ clean_trailing_num(r) for r in rels ]

    types = {
        "entities": { x: { "short": x, "verbose": x } for x in sorted(list(set(ents))) },
        "relations": { x: { "short": x, "verbose": x, "symmetric": False } for x in sorted(list(set(rels))) }
    }

    ## Split 
    np.random.seed(1)
    random.shuffle(spert)
    train, test, dev = np.split(spert, [int(.8*len(spert)), int(.9*len(spert))])

    ## Save
    ner_path = os.path.join(Config.preprocess_dir, 'spert')
    if not os.path.exists(ner_path): os.mkdir(ner_path)
    write_json(list(train), os.path.join(ner_path, 'train.json'))
    write_json(list(dev), os.path.join(ner_path, 'dev.json'))
    write_json(list(test), os.path.join(ner_path, 'test.json'))
    write_json(types, os.path.join(ner_path, 'types.json'))

if __name__ == '__main__':
    main()