import os
import re
import sys
import json
import numpy as np
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils

def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]

    # Get unique relations unioned with event arguments
    rels, args = set(), set()
    regex_trailing_num = r'[0-9]$'
    for ann in annotations:
        rels = rels.union(set([ (v.arg1.get_T().type, v.arg2.get_T().type, 'Relation:'+v.type) for k,v in ann.Rs.items() ]))
        for _, ev in ann.Es.items():
            args = args.union([ (ev.args[0].type, arg.val.get_T().type, 'Argument:'+arg.type) for arg in ev.args[1:]])
    
    all_rels = rels.union(args)
    all_rels.add(('Other', 'Other', 'Other'))
    for rel in list(all_rels):
        if 'Arg' not in rel[2] and any(re.findall(regex_trailing_num, rel[2])):
            rel[2] = re.sub(regex_trailing_num, '', rel[2])

    known_rel_types = set([ (rel[0], rel[1]) for rel in all_rels ])

    # Generate labels + ids for each relation
    relation2id = {}
    id2relation = []
    for rel in all_rels:
        if rel not in relation2id:
            id2relation.append(rel)
            relation2id[rel] = len(relation2id)

    r_bert = [ ann.to_r_bert_format(relation2id, id2relation, known_rel_types, debug=False) for ann in annotations ]
    x=1


    ## Split 
    #np.random.seed(1)
    #train, test, dev = np.split(dygiepp, [int(.8*len(dygiepp)), int(.9*len(dygiepp))])
    
if __name__ == '__main__':
    main()