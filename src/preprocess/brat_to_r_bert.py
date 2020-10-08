import os
import re
import sys
import json
import random
import numpy as np
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils

regex_trailing_num = r'\d'


def write_tsv(lines, file_path):
    with open(file_path, 'w+') as f: 
        for i,l in enumerate(lines, 1):
            f.write(f'{i}\t{l}')


def get_relation_tuple(tp, arg1, arg2):
    if ':Arg' not in tp and any(re.findall(regex_trailing_num, tp)):
        tp = re.sub(regex_trailing_num, '', tp)
    tp = tp.replace('-Name','')
    if arg1.tok_beg_idx < arg2.tok_end_idx:
        return tp+'(E1,E2)'
    return tp+'(E2,E1)'


def main():

    regex_trailing_num = r'\d'
    clean_rel = lambda tp: (re.sub(regex_trailing_num, '', tp) if 'Arg' not in tp and any(re.findall(regex_trailing_num, tp)) else tp).replace('-Name','')

    rel_path = os.path.join(Config.preprocess_dir, 'ctg_data')
    if not os.path.exists(rel_path): 
        os.mkdir(rel_path)

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]

    # Get unique relations unioned with event arguments
    rels, args, known_rel_types = set(), set(), set()
    for ann in annotations:
        rels = rels.union(set([ get_relation_tuple('Relation:'+v.type, v.arg1.get_T(), v.arg2.get_T()) for k,v in ann.Rs.items() ]))
        known_rel_types = known_rel_types.union(set([ (v.arg1.get_T().type, v.arg2.get_T().type, clean_rel(v.type)) for k,v in ann.Rs.items() ]))
        for _, ev in ann.Es.items():
            args = args.union([ get_relation_tuple('Argument:'+arg.type, ev.args[0].get_T(), arg.get_T()) for arg in ev.args[1:]])
            known_rel_types = known_rel_types.union(set([ (ev.args[0].get_T().type, arg.get_T().type, clean_rel(arg.type)) for arg in ev.args[1:] ]))
    
    # Track type labels so BERT won't mess with them in prediction
    with open(os.path.join(rel_path, 'types.tsv'), 'w+') as fout:
        types = set()
        for x1, x2, _ in known_rel_types:
            types.add(x1)
            types.add(x2)
        fout.write('\n'.join(types))

    with open(os.path.join(rel_path, 'relation_combinations.tsv'), 'w+') as fout:
        for x1, x2, x3 in sorted([ x for x in known_rel_types ]):
            fout.write('\t'.join([ x1, x2, x3 ]) + '\n')

    # Generate labels + ids for each relation
    all_rels = set(['Other']).union(rels).union(args)
    relation2id = {}
    id2relation = []
    with open(os.path.join(rel_path, 'relation2id.tsv'), 'w+') as fout:
        for rel in all_rels:
            if rel not in relation2id:
                id2relation.append(rel)
                relation2id[rel] = len(relation2id)
                fout.write(f'{rel}\n')

    rels = []
    known_rel_types_no_arg = set([ (x1, x2) for x1, x2, x3 in known_rel_types ])
    r_bert = [ ann.to_r_bert_format(relation2id, id2relation, known_rel_types_no_arg) for ann in annotations ]
    for rel in r_bert:
        rels += rel

    print(len(rels))

    ## Split
    rels = random.sample(rels, len(rels))
    train, test, dev = np.split(rels, [int(.8*len(rels)), int(.9*len(rels))])
    
    write_tsv(train, os.path.join(rel_path, 'train.tsv'))
    write_tsv(test, os.path.join(rel_path, 'test.tsv'))
    write_tsv(dev, os.path.join(rel_path, 'dev.tsv'))

    
if __name__ == '__main__':
    main()