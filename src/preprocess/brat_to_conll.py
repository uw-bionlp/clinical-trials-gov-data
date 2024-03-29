import os
import sys
import numpy as np
import random
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


def brat_events_to_conll(output_filepath, anns, include_values=True, write_brat=True):
    unq_labels = []
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
                            if include_values and a:
                                label = ev.args[0].val.type + '___' + a.type + ':' + a.val
                            else:
                                label = ev.args[0].val.type
                            labels.append(label)

                        # Ignore Ages embedded in Eq-Comparisons
                        if sorted(labels) == ['Age','Eq-Comparison']:
                            labels = ['Eq-Comparison']
                            t_evs  = [ v for v in evs if tok.i in v.args[0].val.tok_idxs and v.args[0].val.type != 'Age' ]
                            is_start = tok.i == t_evs[0].args[0].val.tok_idxs[0]
                        label = f'{"B" if is_start else "I"}-' + '|'.join(sorted(labels))
                        unq_labels.append(label)

                        brat_rows.add(f'{label[2:]} {t_evs[0].args[0].val.char_beg_idx} {t_evs[0].args[0].val.char_end_idx}\t{t_evs[0].args[0].val.span}')
                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} {label}\n')
                fout.write('\n')

            if write_brat:
                brat_rows = [ f'T{i+1} {t}' for i,t in enumerate(brat_rows) ]
                brat_dir = os.path.join(Path(output_filepath).parent, 'train' if 'train' in output_filepath else 'test')
                text = ann.pretokenized
                to_brat(brat_dir, ann.doc_id, brat_rows, text)
    unq_labels.append('O')
    return list(set(unq_labels))


def brat_entities_to_conll(output_filepath, anns, include_values=True, write_brat=True):
    unq_labels = []
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
                            if include_values and a:
                                label = ent.type + '___' + a.type + ':' + a.val
                            else:
                                label = ent.type
                            labels.append(label)
                        label = f'{"B" if is_start else "I"}-' + '|'.join(sorted(labels))
                        unq_labels.append(label)

                        brat_rows.add(f'{label[2:]} {t_ents[0].char_beg_idx} {t_ents[0].char_end_idx}\t{t_ents[0].span}')
                        fout.write(f'{tok.text} {ann.doc_id} {tok_start} {tok_end} {label}\n')
                fout.write('\n')

            if write_brat:
                brat_rows = [ f'T{i+1} {t}' for i,t in enumerate(brat_rows) ]
                brat_dir = os.path.join(Path(output_filepath).parent, 'train' if 'train' in output_filepath else 'test')
                text = ann.pretokenized
                to_brat(brat_dir, ann.doc_id, brat_rows, text)
    unq_labels.append('O')
    return list(set(unq_labels))


def get_doc_names_from_conll(path):
    doc_ids = set()
    with open(path, 'r', encoding='utf-8') as fin:
        for l in fin.readlines():
            if l.strip():
                doc_id = l.split(' ')[1]
                if doc_id not in doc_ids:
                    doc_ids.add(doc_id)
    return doc_ids


def main():

    conll_path = os.path.join(Config.preprocess_dir, 'conll')
    if not os.path.exists(conll_path): 
        os.mkdir(conll_path)

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]

    # Split 
    np.random.seed(1)
    random.seed(1)
    random.shuffle(annotations)
    _, train, test = np.split(annotations, [ 0, int(.8*len(annotations))])

    events_path = os.path.join(conll_path, 'lct_events_no_val')
    entities_path = os.path.join(conll_path, 'lct_entities_no_val')
    events_brat_path_train = os.path.join(events_path, 'train')
    entities_brat_path_train = os.path.join(entities_path, 'train')
    events_brat_path_valid = os.path.join(events_path, 'test')
    entities_brat_path_valid = os.path.join(entities_path, 'test')

    for p in [ events_path, entities_path, events_brat_path_train, entities_brat_path_train, events_brat_path_valid, entities_brat_path_valid ]:
        if not os.path.exists(p):
            os.mkdir(p)

    evt_labels =  brat_events_to_conll(os.path.join(events_path, 'train.txt'), train, False)
    evt_labels += brat_events_to_conll(os.path.join(events_path, 'test.txt'), test, False)
    with open(os.path.join(events_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(evt_labels)))))

    ent_labels =  brat_entities_to_conll(os.path.join(entities_path, 'train.txt'), train, False)
    ent_labels += brat_entities_to_conll(os.path.join(entities_path, 'test.txt'), test, False)
    with open(os.path.join(entities_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(ent_labels)))))



    
if __name__ == '__main__':
    main()