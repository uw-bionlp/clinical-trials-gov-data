import os
import sys
import spacy
import itertools
sys.path.append(os.path.join(os.getcwd(), 'src'))

from sklearn.metrics import cohen_kappa_score

from preprocess.brat_document import BratDocument
import preprocess.utils as utils

tokenize = spacy.load('en_core_web_sm')


def main():

    print('*** Training data ***')
    nic_raw  = { k:v for k,v in utils.fetch_brat_files(os.path.join('ner', 'archive', 'nic', 'training')).items() }
    tony_raw = { k:v for k,v in utils.fetch_brat_files(os.path.join('ner', 'archive', 'tony', 'training')).items() }
    nic_anns  = [ BratDocument(k, v[0], v[1], tokenize) for k,v in nic_raw.items() ]
    tony_anns = [ BratDocument(k, v[0], v[1], tokenize) for k,v in tony_raw.items() ]
    f1(nic_anns, tony_anns)
    
    print('*** First Tony 100 ***')
    nic_raw = {}
    for d in [ os.path.join(os.getcwd(), 'ner', 'archive', 'nic', 'batch1'), os.path.join(os.getcwd(), 'ner', 'archive', 'nic', 'batch2') ]:
        nic_raw = {**nic_raw, **utils.fetch_brat_files(d)}
    nic_anns = [ BratDocument(k, v[0], v[1], v[2]) for k,v in nic_raw.items() ]

    tony_raw = {}
    for d in [ os.path.join(os.getcwd(), 'ner', 'archive', 'tony', 'batch1'), os.path.join(os.getcwd(), 'ner', 'archive', 'tony', 'batch2') ]:
        tony_raw = {**tony_raw, **utils.fetch_brat_files(d)}
    tony_anns = [ BratDocument(k, v[0], v[1], v[2]) for k,v in tony_raw.items() ]
    f1(nic_anns, tony_anns)

def cohens_kappa(anns1, anns2):
    anns1_conll = list(itertools.chain(*[ to_conll(d).splitlines() for d in anns1 ]))
    anns2_conll = list(itertools.chain(*[ to_conll(d).splitlines() for d in anns2 ]))
    anns1_str_ids = [ [ d.split()[0], d.split()[-1] ] for d in anns1_conll if d != '' ]
    anns2_str_ids = [ [ d.split()[0], d.split()[-1] ] for d in anns2_conll if d != '' ]

    assert len(anns1_str_ids) == len(anns2_str_ids), 'Lengths are different!'

    unq_toks = set([ d[0] for d in anns1_str_ids])
    unq_labels = set([ d[1] for d in anns1_str_ids ] + [ d[1] for d in anns2_str_ids ])

    tok2id = { i:d for i, d in enumerate(unq_toks) }
    label2id = { d:i for i, d in enumerate(unq_labels) }

    anns1_idxs = [ label2id[a[1]] for a in anns1_str_ids ]
    anns2_idxs = [ label2id[a[1]] for a in anns2_str_ids ]
    
    kappa = cohen_kappa_score(anns1_idxs, anns2_idxs)
    print(kappa)
    

def to_conll(ann):
    conll = ''
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
                conll += f'{tok.text} {ann.doc_id} {tok_start} {tok_end} O\n'
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
                conll += f'{tok.text} {ann.doc_id} {tok_start} {tok_end} {label}\n'
        conll += '\n'
    return conll



def f1(anns_gold, anns_eval):
    """ Entities """
    tp, tn, fp, fn = 0, 0, 0, 0
    type_scores = {}
    for doc_gold in anns_gold:
        doc_eval = [ doc for doc in anns_eval if doc.doc_id == doc_gold.doc_id ][0]

        # Precision
        for k,v in doc_eval.Ts.items():
            if not type_scores.get(v.type): type_scores[v.type] = { 'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0 }
            if any([ k2 for k2,v2 in doc_gold.Ts.items() if v2.tok_beg_idx == v.tok_beg_idx and v2.tok_end_idx == v.tok_end_idx and v2.type == v.type ]):
                tp += 1
                type_scores[v.type]['tp'] += 1
            else:
                fp += 1
                type_scores[v.type]['fp'] += 1

        # Recall
        for k,v in doc_gold.Ts.items():
            if not type_scores.get(v.type): type_scores[v.type] = { 'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0 }
            if not any([ k2 for k2,v2 in doc_eval.Ts.items() if v2.tok_beg_idx == v.tok_beg_idx and v2.tok_end_idx == v.tok_end_idx and v2.type == v.type ]):
                fn += 1
                type_scores[v.type]['fn'] += 1

    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * (precision * recall) / (precision + recall)

    print(f'Entities - Overall')
    print(f'    F1: {round(f1*100,1)}')
    print(f'    Precision: {round(precision*100,1)}')
    print(f'    Recall: {round(recall*100,1)}')
    print('')

    #for k,v in sorted(type_scores.items()):
    #    if (v['tp'] + v['fp']) == 0 or (v['tp'] + v['fn']) == 0: 
    #        continue
    #    precision = v['tp'] / (v['tp'] + v['fp'])
    #    recall = v['tp'] / (v['tp'] + v['fn'])
    #    if precision == 0 or recall == 0: 
    #        continue
    #    f1 = 2 * (precision * recall) / (precision + recall)
    #    print(f'    {k}')
    #    print(f'        Precision: {round(precision*100,1)}')
    #    print(f'        Recall: {round(recall*100,1)}')
    #    print(f'        F1: {round(f1*100,1)}')

    """ Relations """
    tp, tn, fp, fn = 0, 0, 0, 0
    type_scores = {}
    for doc_gold in anns_gold:
        doc_eval = [ doc for doc in anns_eval if doc.doc_id == doc_gold.doc_id ][0]

        # Relations - Precision
        for k,v in doc_eval.Rs.items():
            if not type_scores.get(v.type): type_scores[v.type] = { 'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0 }
            if any([ k2 for k2,v2 in doc_gold.Rs.items() if \
                    v2.arg1.get_T().tok_beg_idx == v.arg1.get_T().tok_beg_idx and v2.arg1.get_T().tok_end_idx == v.arg1.get_T().tok_end_idx and \
                    v2.arg2.get_T().tok_beg_idx == v.arg2.get_T().tok_beg_idx and v2.arg2.get_T().tok_end_idx == v.arg2.get_T().tok_end_idx and \
                    v2.type == v.type ]):
                tp += 1
                type_scores[v.type]['tp'] += 1
            else:
                fp += 1
                type_scores[v.type]['fp'] += 1

        # Relations - Recall
        for k,v in doc_gold.Rs.items():
            if not type_scores.get(v.type): type_scores[v.type] = { 'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0 }
            if not any([ k2 for k2,v2 in doc_eval.Rs.items() if \
                    v2.arg1.get_T().tok_beg_idx == v.arg1.get_T().tok_beg_idx and v2.arg1.get_T().tok_end_idx == v.arg1.get_T().tok_end_idx and \
                    v2.arg2.get_T().tok_beg_idx == v.arg2.get_T().tok_beg_idx and v2.arg2.get_T().tok_end_idx == v.arg2.get_T().tok_end_idx and \
                    v2.type == v.type ]):
                fn += 1
                type_scores[v.type]['fn'] += 1

    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * (precision * recall) / (precision + recall)

    print(f'Relations - Overall')
    print(f'    F1: {round(f1*100,1)}')
    print(f'    Precision: {round(precision*100,1)}')
    print(f'    Recall: {round(recall*100,1)}')
    print('')

    #for k,v in sorted(type_scores.items()):
    #    precision = v['tp'] / (v['tp'] + v['fp']) if v['tp'] + v['fp'] > 0 else 0.0
    #    recall = v['tp'] / (v['tp'] + v['fn']) if v['tp'] + v['fn'] > 0 else 0.0
    #    f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0.0
    #    print(f'    {k}')
    #    print(f'        Precision: {round(precision*100,1)}')
    #    print(f'        Recall: {round(recall*100,1)}')
    #    print(f'        F1: {round(f1*100,1)}')
    

if __name__ == '__main__':
    main()
