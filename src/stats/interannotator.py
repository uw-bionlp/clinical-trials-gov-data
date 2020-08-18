import os
import sys
import spacy
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ner.preprocess.brat_document import BratDocument
from ner.preprocess.config import Config
import ner.preprocess.utils as utils

tokenize = spacy.load('en_core_web_sm')

def main():
    nic_dir = os.path.join('ner','nic', 'training')
    tony_dir = os.path.join('ner','tony', 'training')
    nic_data = {}
    tony_data = {}
    
    first_10 = [ 'NCT03930108', 'NCT03930121', 'NCT03930134', 'NCT03930524', 'NCT03930849', 'NCT03930901', 'NCT03931148', 'NCT03931616', 'NCT03931772', 'NCT03931941' ]
    last_10  = [ 'NCT03932045', 'NCT03932929', 'NCT03934008', 'NCT03934034', 'NCT03934151', 'NCT03934346', 'NCT03934385', 'NCT03934424', 'NCT03934554', 'NCT03934593' ]
    to_compare = first_10 + last_10


    # Raw data
    nic_raw  = { k:v for k,v in utils.fetch_brat_files(nic_dir).items() if k in to_compare }
    tony_raw = { k:v for k,v in utils.fetch_brat_files(tony_dir).items() if k in to_compare }

    # Annotations
    nic_ann  = [ BratDocument(k, v[0], v[1], tokenize) for k,v in nic_raw.items() ]
    tony_ann = [ BratDocument(k, v[0], v[1], tokenize) for k,v in tony_raw.items() ]

    ann_gold = nic_ann
    ann_eval = tony_ann

    """ Entities """
    tp, tn, fp, fn = 0, 0, 0, 0
    type_scores = {}
    for doc_gold in ann_gold:
        doc_eval = [ doc for doc in ann_eval if doc.doc_id == doc_gold.doc_id ][0]

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
    print(f'    Precision: {round(precision*100,1)}')
    print(f'    Recall: {round(recall*100,1)}')
    print(f'    F1: {round(f1*100,1)}')
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
    for doc_gold in ann_gold:
        doc_eval = [ doc for doc in ann_eval if doc.doc_id == doc_gold.doc_id ][0]

        # Precision
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

        # Recall
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
    print(f'    Precision: {round(precision*100,1)}')
    print(f'    Recall: {round(recall*100,1)}')
    print(f'    F1: {round(f1*100,1)}')
    print('')

    for k,v in sorted(type_scores.items()):
        precision = v['tp'] / (v['tp'] + v['fp']) if v['tp'] + v['fp'] > 0 else 0.0
        recall = v['tp'] / (v['tp'] + v['fn']) if v['tp'] + v['fn'] > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0.0
        print(f'    {k}')
        print(f'        Precision: {round(precision*100,1)}')
        print(f'        Recall: {round(recall*100,1)}')
        print(f'        F1: {round(f1*100,1)}')

main()


# TODO(ndobb) - frequency stats for each annotation type