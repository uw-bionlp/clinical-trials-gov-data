import os
import re
import sys
import json
import numpy as np
from pathlib import Path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils


def to_brat(output_dir, anns):
    for ann in anns:
        t, a = ann.to_brat()
        with open(os.path.join(output_dir, ann.doc_id+'.txt'), 'w+') as fout:
            fout.write(t)
        with open(os.path.join(output_dir, ann.doc_id+'.ann'), 'w+') as fout:
            fout.write(a)


def brat_events_to_conll(output_filepath, anns):
    with open(output_filepath, 'w+') as fout:
        for ann in anns:
            evs  = [ v for k,v in ann.Es.items() ]
            for sent in ann.sents:
                for tok in sent:
                    t_evs  = [ v for v in evs if tok.i in v.args[0].val.tok_idxs ]
                    tok_start = tok.idx
                    tok_end = tok_start + len(tok.text)
                    if tok.text.strip() == '':
                        continue
                    if not len(t_evs):
                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} O\n')
                    else:
                        is_start = tok.i == t_evs[0].args[0].val.tok_idxs[0]
                        labels = []
                        for ev in t_evs:
                            a = [ v for k,v in ann.As.items() if v.attr_of == ev ]
                            a = a[0] if len(a) else None
                            if a:
                                label = ev.args[0].val.type + '___' + a.type + ':' + a.val
                            else:
                                label = ev.args[0].val.type
                            labels.append(label)
                        label = f'{"B" if is_start else "I"}-' + '|'.join(sorted(labels))

                        # For now, ignore Ages embedded in Eq-Comparisons
                        if label == 'B-Age|Eq-Comparison':
                            label = 'I-Eq-Comparison'

                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} {label}\n')
                fout.write('\n')


def brat_entities_to_conll(output_filepath, anns):
    with open(output_filepath, 'w+') as fout:
        for ann in anns:
            evs  = [ v.args[0].val for k,v in ann.Es.items() ]
            ents = [ v for k,v in ann.Ts.items() if v not in evs ] 
            for sent in ann.sents:
                for tok in sent:
                    t_ents = [ v for v in ents if tok.i in v.tok_idxs ]
                    tok_start = tok.idx
                    tok_end = tok_start + len(tok.text)
                    if tok.text.strip() == '':
                        continue
                    if not len(t_ents):
                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} O\n')
                    else:
                        is_start = tok.i == t_ents[0].tok_idxs[0]
                        labels = []
                        for ent in t_ents:
                            a = [ v for k,v in ann.As.items() if v.attr_of == ent ]
                            a = a[0] if len(a) else None
                            if a:
                                label = ent.type + '___' + a.type + ':' + a.val
                            else:
                                label = ent.type
                            labels.append(label)
                        label = f'{"B" if is_start else "I"}-' + '|'.join(sorted(labels))
                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} {label}\n')
                fout.write('\n')


def main():

    conll_path = os.path.join(Config.preprocess_dir, 'conll')
    if not os.path.exists(conll_path): 
        os.mkdir(conll_path)

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]

    ## Split 
    np.random.seed(1)
    _, train, test = np.split(annotations, [ 0, int(.8*len(annotations))])

    events_path = os.path.join(conll_path, 'events')
    entities_path = os.path.join(conll_path, 'entities')
    events_brat_path_train = os.path.join(events_path, 'train')
    entities_brat_path_train = os.path.join(entities_path, 'train')
    events_brat_path_valid = os.path.join(events_path, 'valid')
    entities_brat_path_valid = os.path.join(entities_path, 'valid')

    for p in [ events_path, entities_path, events_brat_path_train, entities_brat_path_train, events_brat_path_valid, entities_brat_path_valid ]:
        if not os.path.exists(p):
            os.mkdir(p)

    brat_events_to_conll(os.path.join(events_path, 'train_spacy.txt'), train)
    brat_entities_to_conll(os.path.join(entities_path, 'train_spacy.txt'), train)
    brat_events_to_conll(os.path.join(events_path, 'valid_spacy.txt'), test)
    brat_entities_to_conll(os.path.join(entities_path, 'valid_spacy.txt'), test)

    to_brat(events_brat_path_train, train)
    to_brat(entities_brat_path_train, train)
    to_brat(events_brat_path_valid, test)
    to_brat(entities_brat_path_valid, test)
    
    
if __name__ == '__main__':
    main()