import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ner.preprocess.brat_document import BratDocument
from ner.preprocess.config import Config
import ner.preprocess.utils as utils

def main():

    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]

    unq_ev_types = set()
    for ann in annotations:
        for k, v in ann.Es.items():
            unq_ev_types.add(v.args[0].type)
    total_docs = len(annotations)

    print(f'\nTotal docs: {total_docs}')

    ''' Entities '''
    print('\nEntities\n--------')
    ents = {}
    for ann in annotations:
        for _, v in ann.Ts.items():
            if v.type in unq_ev_types: continue
            if v.type in ents:
                ents[v.type] += 1
            else:
                ents[v.type] = 1

    print('{:<25} {:<5} {:<10}'.format('TAG', 'COUNT', 'FREQ'))
    for k, v in sorted(ents.items(), key=lambda x: x[1], reverse=True):
        print('{:<25} {:<5} {:<10}'.format(k, v, round(v / total_docs, 3)))

    ''' Relations '''
    print('\nRelations\n---------')
    rels = {}
    for ann in annotations:
        for _, v in ann.Rs.items():
            if v.type in rels:
                rels[v.type] += 1
            else:
                rels[v.type] = 1

    print('{:<25} {:<5} {:<10}'.format('TAG', 'COUNT', 'FREQ'))
    for k, v in sorted(rels.items(), key=lambda x: x[1], reverse=True):
        print('{:<25} {:<5} {:<10}'.format(k, v, round(v / total_docs, 3)))

    ''' Events '''
    print(f'\nEvents\n------')
    evs = {}
    for ann in annotations:
        for _, v in ann.Es.items():
            tp = v.args[0].type
            if tp in evs:
                evs[tp] += 1
            else:
                evs[tp] = 1

    print('{:<25} {:<5} {:<10}'.format('TAG', 'COUNT', 'FREQ'))
    for k, v in sorted(evs.items(), key=lambda x: x[1], reverse=True):
        print('{:<25} {:<5} {:<10}'.format(k, v, round(v / total_docs, 3)))

main()
