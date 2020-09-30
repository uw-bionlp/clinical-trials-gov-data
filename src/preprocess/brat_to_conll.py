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


def to_brat(output_dir, doc_id, Ts, text):
    with open(os.path.join(output_dir, doc_id+'.txt'), 'w+') as fout:
        fout.write(text)
    with open(os.path.join(output_dir, doc_id+'.ann'), 'w+') as fout:
        fout.write('\n'.join(Ts)) 


def brat_events_to_conll(output_filepath, anns):
    with open(output_filepath, 'w+') as fout:
        for ann in anns:
            brat_rows = set()
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
                        labels, types_seen = [], set()
                        for ev in t_evs:
                            if ev.args[0].val.type in types_seen:
                                continue
                            types_seen.add(ev.args[0].val.type)
                            a = [ v for k,v in ann.As.items() if v.attr_of == ev ]
                            a = a[0] if len(a) else None
                            if a:
                                label = ev.args[0].val.type + '___' + a.type + ':' + a.val
                            else:
                                label = ev.args[0].val.type
                            labels.append(label)
                        label = f'{"B" if is_start else "I"}-' + '|'.join(sorted(labels))

                        # For now, ignore Ages embedded in Eq-Comparisons
                        if label[2:] == 'Age|Eq-Comparison':
                            label = label[:2] + 'Eq-Comparison'

                        brat_rows.add(f'{label[2:]} {t_evs[0].args[0].val.char_beg_idx} {t_evs[0].args[0].val.char_end_idx}\t{t_evs[0].args[0].val.span}')
                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} {label}\n')
                fout.write('\n')

            brat_rows = [ f'T{i+1} {t}' for i,t in enumerate(brat_rows) ]
            brat_dir = os.path.join(Path(output_filepath).parent, 'train' if 'train' in output_filepath else 'valid')
            text = ann.pretokenized
            to_brat(brat_dir, ann.doc_id, brat_rows, text)



def brat_entities_to_conll(output_filepath, anns):
    with open(output_filepath, 'w+') as fout:
        for ann in anns:
            brat_rows = set()
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
                        labels, types_seen = [], set()
                        for ent in t_ents:
                            if ent.type in types_seen:
                                continue
                            types_seen.add(ent.type)
                            a = [ v for k,v in ann.As.items() if v.attr_of == ent ]
                            a = a[0] if len(a) else None
                            if a:
                                label = ent.type + '___' + a.type + ':' + a.val
                            else:
                                label = ent.type
                            labels.append(label)
                        label = f'{"B" if is_start else "I"}-' + '|'.join(sorted(labels))

                        brat_rows.add(f'{label[2:]} {t_ents[0].char_beg_idx} {t_ents[0].char_end_idx}\t{t_ents[0].span}')
                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} {label}\n')
                fout.write('\n')

            brat_rows = [ f'T{i+1} {t}' for i,t in enumerate(brat_rows) ]
            brat_dir = os.path.join(Path(output_filepath).parent, 'train' if 'train' in output_filepath else 'valid')
            text = ann.pretokenized
            to_brat(brat_dir, ann.doc_id, brat_rows, text)


def quality_check(annotations):
    t_s = [ (x,a) for a in annotations for _,x in a.Ts.items() ]
    a_s = [ x for a in annotations for _,x in a.As.items() ]
    for ent in [ 'Severity', 'Stability', 'Eq-Operator' ]:
        x_s = [ t for t in t_s if t[0].type == ent ]
        for x in x_s: 
            a = [ a for a in a_s if a.attr_of == x[0] ]
            a = a[0] if len(a) else None
            if a == None:
                print(x[1])

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

    
if __name__ == '__main__':
    main()