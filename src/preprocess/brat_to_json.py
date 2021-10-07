import os
import sys
import spacy
import json
from random import shuffle
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils

tokenize = spacy.load('en_core_web_sm')


def main():
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]

    shuffle(annotations)
    annotations = annotations[:150]

    entities = []
    relations = []

    for ann in annotations:
        #d = { 'id': ann.doc_id, 'entities': [], 'relations': [] }
        #d['entities'] = [[]] * max([ t.sent_idx for _, t in ann.Ts.items() ])
        ann_rels = []
                
        # Relations/Args
        for k, r in ann.Rs.items():
            rel = { 'doc_id': ann.doc_id, 'id': r.id, 'type': r.type, 'metatype': 'Relation', 'subj': r.arg1.get_T().id, 'obj': r.arg2.get_T().id  }
            relations.append(rel)
            ann_rels.append(rel)

        for k, e in ann.Es.items():
            for i, arg in enumerate(e.args[1:], 1):
                arg_rel = { 'doc_id': ann.doc_id, 'id': f'{e.id}_{i}', 'type': arg.type, 'metatype': 'Argument', 'subj': e.id, 'obj': arg.val.get_T().id }
                relations.append(arg_rel)
                ann_rels.append(rel)

        # Entities
        for k, t in sorted(ann.Ts.items(), key=lambda x: x[1].tok_beg_idx):
            e = { 'doc_id': ann.doc_id, 'id': t.id, 'span': t.span, 'attr_type': None, 'attr_val': None,
                  'sent_idx': t.line, 'type': t.type, 'metatype': 'Entity', 'relations': [], 'relation_ofs': [] }
            a       = [ a for _, a in ann.As.items() if a.attr_of == t ]
            ents    = [ e for _, e in ann.Es.items() if any(e.args) and e.args[0].val == t ]
            rels    = set([ r['id'] for r in ann_rels if r['subj'] == e['id'] ])
            rel_ofs = set([ r['id'] for r in ann_rels if r['obj'] == e['id'] ])
            if any(a):    e['attr_type'] =a[0].type; e['attr_val'] = a[0].val
            if any(ents): e['metatype'] = 'Trigger'
            for rel_id in rels:    e['relations'].append(rel_id)
            for rel_id in rel_ofs: e['relation_ofs'].append(rel_id)

            entities.append(e)

            #for tok in t.span.lower().split():
            #    if tok in data['tok_freq']:
            #        data['tok_freq'][tok] += 1
            #    else:
            #        data['tok_freq'][tok] = 1
        #data['documents'].append(d)

    # Token frequencies
    #with open('clinical_trials_annotation_tok_freqs.json', 'w+') as fout:
    #    json.dump(data['tok_freq'], fout)

    # Entities & Relations
    with open('clinical_trials_annotation_entities.json', 'w+') as fout:
        json.dump(entities, fout)
    with open('clinical_trials_annotation_relations.json', 'w+') as fout:
        json.dump(relations, fout)





if __name__ == '__main__':
    main()